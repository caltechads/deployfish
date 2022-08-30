import sys
from typing import List, Dict, TYPE_CHECKING, cast, Any, Optional
from deployfish.types import SupportsModel
from deployfish.exceptions import SchemaException

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


if TYPE_CHECKING:
    from .abstract import Model, Manager
    from .ecs import ContainerDefinition

# ----------------------
# Protocols
# ----------------------

# It is so stupid that I have to do these protocols to make type checking happy on mixins
# We really want an Intersection[] type, but one does not exist yet.

class SupportsTags(SupportsModel, Protocol):

    _tags: Dict[str, str]

    @property
    def tags(self) -> Dict[str, str]:
        ...

    def import_tags(self, aws_tags: List[Dict[str, str]]) -> None:
        ...


# ----------------------
# Mixins
# ----------------------


class TagsManagerMixin:

    def get_tags(self, obj: "Model") -> List[Dict[str, str]]:
        raise NotImplementedError

    def save_tags(self, obj: "Model") -> None:
        raise NotImplementedError


class TagsMixin:

    objects: "Manager"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tags: Dict[str, str] = {}
        key = None
        if 'tags' in self.data:
            key = 'tags'
        elif 'Tags' in self.data:
            key = 'Tags'
        if key:
            self.import_tags(self.data[key])

    @property
    def tags(self) -> Dict[str, str]:
        return self._tags

    def get_tags(self) -> None:
        if hasattr(self.objects, 'get_tags'):
            self.import_tags(getattr(self.objects, 'get_tags')(self))
        else:
            raise NotImplementedError

    def import_tags(self, aws_tags: List[Dict[str, str]]) -> None:
        for tag in aws_tags:
            if 'Key' in tag:
                self._tags[tag['Key']] = tag['Value']
            else:
                self._tags[tag['key']] = tag['value']

    def save_tags(self: SupportsTags) -> None:
        if hasattr(self.objects, 'save_tags'):
            getattr(self.objects, 'save_tags')(self)
        else:
            raise NotImplementedError

    def render_tags(self: SupportsTags) -> List[Dict[str, str]]:
        data: List[Dict[str, str]] = []
        for key, value in list(self.tags.items()):
            data.append({'key': key, 'value': value})
        return data


class TaskDefinitionFARGATEMixin:

    data: Dict[str, Any]
    containers: List["ContainerDefinition"]

    VALID_FARGATE_CPU: List[int] = [256, 512, 1024, 2048, 4096]
    VALID_FARGATE_MEMORY: Dict[int, List[int]] = {
        256: [512, 1024, 2048],
        512: [1024, 2048, 3072, 4096],
        1024: [2048, 3072, 4096, 5120, 6144, 7168, 8192],
        2048: [4096, 5120, 6144, 7168, 8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384],
        4096: [8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384, 17408, 18432, 19456,
               20480, 21504, 22528, 23552, 24576, 25600, 26624, 27648, 28672, 29696, 30720]
    }

    def is_fargate(self) -> bool:
        """
        If this is a FARGATE task definition, return True.  Otherwise return False.

        :rtype: bool
        """
        return 'requiresCompatibilities' in self.data and self.data['requiresCompatibilities'] == ['FARGATE']

    def _get_container_cpu_usage(self, container_data: List[Dict[str, Any]]) -> int:
        """
        Return the minimum necessary cpu for our task by summing up 'cpu' from each of our task's containers.

        :param container_data list(dict(str, *)): the list of ContainerDefinition.data dicts to parse

        :rtype: int
        """
        max_container_cpu: int = 0
        for c in container_data:
            if 'cpu' in c:
                max_container_cpu += cast(int, c['cpu'])
        # Now find the smallest memory size for our CPU class that fits container_memory
        return max_container_cpu

    def _set_fargate_task_cpu(
        self,
        cpu_required: int,
        source: Dict[str, Any] = None
    ) -> Optional[int]:
        """
        For FARGATE tasks, task cpu is required and must be one of the values listed in self.VALID_FARGATE_CPU.  In this
        case, if 'cpu' is not provided by upstream, add up all the 'cpu' on the task's containers and choose the next
        biggest value from self.VALID_FARGATE_CPU.  If 'cpu' is provided but is not one of the valid values, raise
        self.SchemaException.

        :param cpu_required int: the minimum amount of cpu required to run all containers, in MB
        :param source dict(str, *): (optional) the data source for computing task memory.  If None, use self.data
        """
        if not source:
            source = self.data
        cpu = None
        if 'cpu' in self.data:
            try:
                cpu = int(self.data['cpu'])
            except ValueError:
                raise SchemaException('Task cpu must be an integer')
            if cpu not in self.VALID_FARGATE_CPU:
                raise SchemaException(
                    'Task cpu of {}MB is not valid for FARGATE tasks.  Choose one of {}'.format(
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

    def _set_ec2_task_cpu(
        self,
        source: Dict[str, Any] = None
    ) -> Optional[int]:
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
                raise SchemaException('Task cpu must be an integer')
        return cpu

    def set_task_cpu(
        self,
        data: Dict[str, Any],
        container_data: List[Dict[str, Any]],
        source: Dict[str, Any] = None
    ) -> None:
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
            cpu = self._set_fargate_task_cpu(cpu_required, source=source)
        else:
            cpu = self._set_ec2_task_cpu(source=source)
        if cpu is not None:
            if cpu_required > cpu:
                raise SchemaException(
                    'You set task cpu to {} but your container cpu sums to {}. Task cpu must be greater than the sum of container cpu.'.format(  # pylint:disable=line-too-long
                        cpu,
                        cpu_required
                    )
                )
            # we calculate cpu as an int, but register_task_definition wants a str
            data['cpu'] = str(cpu)

    def _get_container_memory_usage(self, container_data: List[Dict[str, Any]]) -> int:
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

    def _set_fargate_task_memory(
        self,
        data: Dict[str, Any],
        memory_required: int,
        source: Dict[str, Any] = None
    ) -> Optional[int]:
        """
        Return the value we should set for our ``TaskDefintion`` memory.

        Given ``memory_required`` in MB, figure out what FARGATE memory value
        is most appropriate given the value of ``cpu`` in ``data``.

        For FARGATE tasks, AWS requires this to be one of the values listed in
        ``self.VALID_FARGATE_MEMORY[data['cpu']]``.  In this case, if ``memory``
        is not in ``data``, figure out what the maximum required memory is by
        adding up memory requirements for our containers and choosing the next
        largest memory value from ``self.VALID_FARGATE_MEMORY[data['cpu']]``.

        Args:
            data: the ``TaskDefinition.data`` dict to modify
            memory_required: the minimum amount of memory required to hold all containers, in MB

        Keyword Arguments:
            source: the data source for computing task memory.  If None, use ``data``

        Raises:
            AbstractAdapter.SchemaException: If ``memory`` is in ``data`` but is
                not one of the valid values

        Returns:
            The FARGATE memory setting
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
                raise SchemaException(
                    'When using the FARGATE launch_type with task cpu={}, the maximum memory available is {}MB, but your containers need a minimum of {}MB. Set your task cpu to one of {}.'.format(   # noqa:E501  # pylint:disable=line-too-long
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
                raise SchemaException('Task memory must be an integer')
            if memory not in self.VALID_FARGATE_MEMORY[cpu]:
                raise SchemaException(
                    'When using the FARGATE launch_type with task cpu={}, your requested task memory of {}MB is not valid. Valid task memory values for that cpu level are: {}'.format(  # noqa:E501  # pylint:disable=line-too-long
                        cpu,
                        memory,
                        ', '.join([str(m) for m in self.VALID_FARGATE_MEMORY[cpu]])
                    )
                )
        return memory

    def _set_ec2_task_memory(self, source: Dict[str, Any] = None) -> Optional[int]:
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
                raise SchemaException('Task memory must be an integer')
        return memory

    def set_task_memory(
        self,
        data: Dict[str, Any],
        container_data: List[Dict[str, Any]],
        source: Dict[str, Any] = None
    ) -> None:
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
            memory = self._set_ec2_task_memory(source=source)
        if memory is not None:
            if memory_required > 0 and memory < memory_required:
                raise SchemaException(
                    'Task memory is {}MB but your container memory sums to {}MB. Task memory must be greater than the sum of container memory.'.format(  # noqa:E501  # pylint:disable=line-too-long
                        memory,
                        memory_required
                    )
                )
            # We calculate memory as an int, but register_task_definition() wants a str
            data['memory'] = str(memory)

    def autofill_fargate_parameters(self, data: Dict[str, Any], source: Dict[str, Any] = None) -> None:
        container_data = [c.data for c in self.containers]
        self.set_task_cpu(data, container_data, source=source)
        self.set_task_memory(data, container_data, source=source)
