from deployfish.exceptions import SchemaException


class TagsManagerMixin(object):

    def get_tags(self, obj):
        raise NotImplementedError

    def save_tags(self, obj):
        raise NotImplementedError


class TagsMixin(object):

    def __init__(self, data, **kwargs):
        super(TagsMixin, self).__init__(data, **kwargs)
        self._tags = {}
        key = None
        if 'tags' in self.data:
            key = 'tags'
        elif 'Tags' in self.data:
            key = 'Tags'
        if key:
            self.import_tags(self.data[key])

    @property
    def tags(self):
        return self._tags

    def get_tags(self):
        if hasattr(self.objects, 'get_tags'):
            self.import_tags(self.objects.get_tags(self))
        else:
            raise NotImplementedError

    def import_tags(self, aws_tags):
        for tag in aws_tags:
            if 'Key' in tag:
                self._tags[tag['Key']] = tag['Value']
            else:
                self._tags[tag['key']] = tag['value']

    def save_tags(self):
        if hasattr(self.objects, 'save_tags'):
            self.objects.save_tags(self)
        else:
            raise NotImplementedError

    def render_tags(self):
        data = []
        for key, value in self.tags.items():
            data.append({'key': key, 'value': value})
        return data


class TaskDefinitionFARGATEMixin(object):

    class SchemaException(SchemaException):
        pass

    VALID_FARGATE_CPU = [256, 512, 1024, 2048, 4096]
    VALID_FARGATE_MEMORY = {
        256: [512, 1024, 2048],
        512: [1024, 2048, 3072, 4096],
        1024: [2048, 3072, 4096, 5120, 6144, 7168, 8192],
        2048: [4096, 5120, 6144, 7168, 8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384],
        4096: [8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384, 17408, 18432, 19456,
               20480, 21504, 22528, 23552, 24576, 25600, 26624, 27648, 28672, 29696, 30720]
    }

    def is_fargate(self):
        """
        If this is a FARGATE task definition, return True.  Otherwise return False.

        :rtype: bool
        """
        return 'requiresCompatibilities' in self.data and self.data['requiresCompatibilities'] == ['FARGATE']

    def _get_container_cpu_usage(self, container_data):
        """
        Return the minimum necessary cpu for our task by summing up 'cpu' from each of our task's containers.

        :param container_data list(dict(str, *)): the list of ContainerDefinition.data dicts to parse

        :rtype: int
        """
        max_container_cpu = 0
        for c in container_data:
            if 'cpu' in c:
                max_container_cpu += c['cpu']
        # Now find the smallest memory size for our CPU class that fits container_memory
        return max_container_cpu

    def _set_fargate_task_cpu(self, data, cpu_required, source=None):
        """
        For FARGATE tasks, task cpu is required and must be one of the values listed in self.VALID_FARGATE_CPU.  In this
        case, if 'cpu' is not provided by upstream, add up all the 'cpu' on the task's containers and choose the next
        biggest value from self.VALID_FARGATE_CPU.  If 'cpu' is provided but is not one of the valid values, raise
        self.SchemaException.

        :param data dict(str, *): the TaskDefinition.data dict to modify
        :param cpu_required int: the minimum amount of cpu required to run all containers, in MB
        :param source dict(str, *): (optional) the data source for computing task memory.  If None, use self.data

        :rtype: str
        """
        if not source:
            source = self.data
        cpu = None
        if 'cpu' in self.data:
            try:
                cpu = int(self.data['cpu'])
            except ValueError:
                raise self.SchemaException('Task cpu must be an integer')
            if cpu not in self.VALID_FARGATE_CPU:
                raise self.SchemaException(
                    'Task cpu of {}MB is not valid for FARGATE tasks.  Choose one of ()'.format(
                        cpu,
                        ', '.join([str(c) for c in self.VALID_FARGATE_CPU])
                    )
                )
        else:
            for fg_cpu in self.VALID_FARGATE_CPU:
                if fg_cpu >= cpu_required:
                    cpu = fg_cpu
                    break
        return cpu

    def _set_ec2_task_cpu(self, data, cpu_required, source=None):
        """
        For EC2 tasks, set task cpu if 'cpu' is provided, don't set otherwise.

        If 'cpu' was supplied by the user but it is less than the sum of the container 'cpu' settings, raise
        self.SchemaException.

        :param data dict(str, *): the TaskDefinition.data dict to modify
        :param cpu_required int: the minimum amount of cpu required to run all containers, in MB
        :param source dict(str, *): (optional) the data source for computing task memory.  If None, use self.data

        :rtype: Union[int, None]
        """
        if not source:
            source = self.data
        cpu = None
        if 'cpu' in self.data:
            try:
                cpu = int(self.data['cpu'])
            except ValueError:
                raise self.SchemaException('Task cpu must be an integer')
        return cpu

    def set_task_cpu(self, data, container_data, source=None):
        """
        Set data['cpu'], the task level cpu requirement, based on whether this is a FARGATE task or an EC2 task.

        :param data dict(str, *): the TaskDefinition.data dict to modify
        :param container_data list(dict(str, *)): the list of ContainerDefinition.data dicts to parse
        :param source dict(str, *): (optional) the data source for computing task cpu.  If None, use self.data.
        """
        if not source:
            source = self.data
        cpu_required = self._get_container_cpu_usage(container_data)
        if self.is_fargate():
            cpu = self._set_fargate_task_cpu(data, cpu_required, source=source)
        else:
            cpu = self._set_ec2_task_cpu(data, cpu_required, source=source)
        if cpu is not None:
            if cpu_required > cpu:
                raise self.SchemaException(
                    'You set task cpu to {} but your container cpu sums to {}. Task cpu must be greater than the sum of container cpu.'.format(  # noqa:E501
                        cpu,
                        cpu_required
                    )
                )
            # we calculate cpu as an int, but register_task_definition wants a str
            data['cpu'] = str(cpu)

    def _get_container_memory_usage(self, container_data):
        """
        Find the minimum necessary memory and maximum necessary memory for our task by looking at
        'memoryReservation' and 'memory' (respectively) on each of our task's containers.

        Return the maximum of the two sums.

        :param container_data list(dict(str, *)): the list of ContainerDefinition.data dicts to parse

        :rtype: int
        """
        min_container_memory = 0
        max_container_memory = 0
        for c in container_data:
            if 'memory' in c:
                max_container_memory += c['memory']
            if 'memoryReservation' in c:
                min_container_memory += c['memoryReservation']
        # Now find the smallest memory size for our CPU class that fits container_memory
        return max(min_container_memory, max_container_memory)

    def _set_fargate_task_memory(self, data, memory_required, source=None):
        """
        Return the value we should set for our TaskDefintion memory.

        For FARGATE tasks, AWS requires this to be one of the values listed in self.VALID_FARGATE_MEMORY[data['cpu']].
        In this case, if 'memory' is not provided, figure out what the maximum required memory is by adding up memory
        requirements for our containers and choosing the next largest memory value from
        self.VALID_FARGATE_MEMORY[data['cpu']].  If 'memory' is provided but is not one of the valid values, raise
        self.SchemaException.

        :param data dict(str, *): the TaskDefinition.data dict to modify
        :param memory_required int: the minimum amount of memory required to hold all containers, in MB
        :param source dict(str, *): (optional) the data source for computing task memory.  If None, use self.data

        :rtype: int
        """
        if not source:
            source = self.data
        memory = None
        cpu = int(data['cpu'])
        if 'memory' not in self.data:
            if memory_required == 0:
                memory = self.VALID_FARGATE_MEMORY[cpu][0]
            else:
                for mem in self.VALID_FARGATE_MEMORY[cpu]:
                    if mem >= memory_required:
                        memory = mem
                        break
            if memory is None:
                cpu_index = self.VALID_FARGATE_CPU.index(cpu) + 1
                # FIXME: find the lowest valid fargate CPU level that supports the amount of memory we need
                raise self.SchemaException(
                    'When using the FARGATE launch_type with task cpu={}, the maximum memory available is {}MB, but your containers need a minimum of {}MB. Set your task cpu to one of {}.'.format(   # noqa:E501
                        cpu,
                        self.VALID_FARGATE_MEMORY[cpu][-1],
                        memory_required,
                        ", ".join([str(cpu) for cpu in self.VALID_FARGATE_CPU[cpu_index:]])
                    )
                )
        else:
            try:
                memory = int(self.data['memory'])
            except ValueError:
                raise self.SchemaException('Task memory must be an integer')
            if memory not in self.VALID_FARGATE_MEMORY[cpu]:
                raise self.SchemaException(
                    'When using the FARGATE launch_type with task cpu={}, your requested task memory of {}MB is not valid. Valid task memory values for that cpu level are: {}'.format(  # noqa:E501
                        cpu,
                        memory,
                        ', '.join([str(m) for m in self.VALID_FARGATE_MEMORY[cpu]])
                    )
                )
        return memory

    def _set_ec2_task_memory(self, data, source=None):
        """
        For EC2 tasks, set task memory if 'memory' is provided, don't set otherwise.
        """
        if not source:
            source = self.data
        memory = None
        if 'memory' in self.data:
            try:
                memory = int(self.data['memory'])
            except ValueError:
                raise self.SchemaException('Task memory must be an integer')
        return memory

    def set_task_memory(self, data, container_data, source=None):
        """
        Set data['memory'], the task level memory requirement.

        .. note::

            If this is a FARGATE task, before calling this method you must first have set data['cpu'] to a valid value
            for FARGATE tasks.
        """
        if not source:
            source = self.data
        memory_required = self._get_container_memory_usage(container_data)
        if self.is_fargate():
            memory = self._set_fargate_task_memory(data, memory_required, source=source)
        else:
            memory = self._set_ec2_task_memory(data, source=source)
        if memory is not None:
            if memory_required > 0 and memory < memory_required:
                raise self.SchemaException(
                    'Task memory is {}MB but your container memory sums to {}MB. Task memory must be greater than the sum of container memory.'.format(  # noqa:E501
                        memory,
                        memory_required
                    )
                )
            # We calculate memory as an int, but register_task_definition() wants a str
            data['memory'] = str(memory)

    def autofill_fargate_parameters(self, data, source=None):
        container_data = [c.data for c in self.containers]
        self.set_task_cpu(data, container_data, source=source)
        self.set_task_memory(data, container_data, source=source)
