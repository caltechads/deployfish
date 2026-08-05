from typing import Any

from deployfish.core.models import EventScheduleRule, TaskDefinition
from deployfish.core.models.ecs import Service

from .common import AbstractTaskAdapter


class ServiceHelperTaskAdapter(AbstractTaskAdapter):
    """
    The problem here is that, unlike all our other adapters, we need to create

    Args:
        data: data.
        service: service.

    """

    def __init__(self, data: dict[str, Any], service: Service):
        """
        Args:
            data: the ``tasks:`` section from our service definition in deployfish.yml
            service: the :py:class:`deployfish.core.models.ecs.Service` for
                which we are building helper tasks

        """
        #: Data.
        self.data = data
        #: Service.
        self.service = service

    def _set(
        self,
        data: dict[str, Any],
        task: dict[str, Any],
        yml_key: str,
        data_key: str,
        source: dict[str, Any] | None = None,
    ) -> None:
        """
        Set a ``data[data_key]`` on the dict ``data`` by looking at both
        ``task`` and ``source``.

        If ``task[yml_key]`` exists, set ``data[data_key]`` to that value.
        Else if ``source[yml_key`]`` exists, set ``data[data_key]`` to THAT value.
        Else if ``source[data_key]`` exists, set ``data[data_key]`` to THAT value.
        Else, do nothing.

        .. note::

            This is called ``_set`` because it overrides Adapter.set(), but has
            different args.

        If ``source`` is ``None``, we set ``source`` to `self.service.data`.

        Args:
            data: data.
            task: task.
            yml_key: yml key.
            data_key: data key.
            source: source.

        """
        if not source:
            source = self.service.data
        if yml_key in task:
            data[data_key] = task[yml_key]
        elif yml_key in source:
            data[data_key] = source[yml_key]
        elif data_key in source:
            data[data_key] = source[data_key]

    def get_data(
        self,
        data: dict[str, Any],
        task: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> None:
        """
        Construct ``data`` so that it can be used for constructing our
        :py:class:`deployfish.core.models.ecs.ServiceHelperTask` parameters by
        combining data from an existing
        :py:class:`deployfish.core.models.ecs.TaskDefinition` with configuration
        from deployfish.yml.

        Args:
            data: the dict we are building
            task: the task configuration from deployfish.yml

        Keyword Args:
            source: the data from the previous set of Task parameters.  If not
                provided, ``self.service.data``.

        """
        if not source:
            source = self.service.data
        self._set(data, task, "cluster", "cluster", source=source)
        if "vpc_configuration" in task:
            data["networkConfiguration"] = {}
            data["networkConfiguration"]["awsvpcConfiguration"] = (
                self.get_vpc_configuration(source=task["vpc_configuration"])
            )
        elif "networkConfiguration" in source:
            data["networkConfiguration"] = {}
            data["networkConfiguration"]["awsvpcConfiguration"] = source[
                "networkConfiguration"
            ]["awsvpcConfiguration"]
        self._set(data, task, "launch_type", "launchType", source=source)
        if "launchType" in data and data["launchType"] == "FARGATE":
            self._set(data, task, "platform_version", "platformVersion", source=source)
            if "platformVersion" not in data:
                data["platformVersion"] = "LATEST"
        else:
            # capacity_provider_strategy and launch_type are mutually exclusive
            self._set(
                data,
                task,
                "capacity_provider_strategy",
                "capacityProviderStrategy",
                source=source,
            )
        self._set(
            data, task, "placement_constraints", "placementConstraints", source=source
        )
        self._set(data, task, "placement_strategy", "placementStrategy", source=source)
        self._set(data, task, "group", "group", source=source)
        if "count" in task:
            data["count"] = task["count"]
        self._set(data, task, "schedule", "schedule", source=source)
        self._set(data, task, "schedule_role", "schedule_role", source=source)

    def update_container_environments(
        self, task_definition: TaskDefinition, extra_environment: dict[str, str]
    ) -> None:
        """
        Update the deployfish-specific environment variables in the container
        environment for each container in `task_definition`.

        * Remove DEPLOYFISH_SERVICE_NAME
        * Add DEPLOYFISH_TASK_NAME
        * Update DEPLOYFISH_ENVIRONMENT and DEPLOYFISH_CLUSTER_NAME as necessary

        Args:
            task_definition: task definition.
            extra_environment: extra environment.

        """
        for container in task_definition.containers:
            environment = []
            for var in container.data["environment"]:
                if var["name"] == "DEPLOYFISH_SERVICE_NAME":
                    environment.append(
                        {
                            "name": "DEPLOYFISH_TASK_NAME",
                            "value": extra_environment["DEPLOYFISH_TASK_NAME"],
                        }
                    )
                else:
                    if var["name"] in extra_environment:
                        var["value"] = extra_environment[var["name"]]
                    environment.append(var)
            container.data["environment"] = environment

    def _get_base_task_data(
        self, task_data: dict[str, Any], service_td: TaskDefinition
    ) -> tuple[dict[str, Any], TaskDefinition]:
        """
        Build a dict that takes info from the service and overlays the generic
        (not command specific) task data to build the parameters we'll need when
        running the task.  Also build a new TaskDefinition object that is the
        service's TaskDefinition overlaid with the changes from the generic task
        data.

        Args:
            task_data: the generic helper task data
            service_td: the Service's
                :py:class:`deployfish.core.models.ecs.TaskDefinition` object

        Returns:
            A 2-tuple: dict of parameters for the factory method of
            :py:class:`deployfish.core.models.ecs.ServiceHelperTask`, and the
            new TaskDefinition object

        """
        data_base: dict[str, Any] = {}
        # first, extract whatever we can from self.service
        self.get_data(data_base, task_data)
        data_base["service"] = self.service.pk
        # This base_td_overlay here should be just the things we want to change
        # from the service's TaskDefinition
        base_td_overlay = TaskDefinition.new(task_data, "deployfish", partial=True)
        # Then we add the service's TaskDefinition to the base_td_overlay to get the
        # one for the ServiceHelperTask
        base_td = service_td + base_td_overlay
        base_td.data["family"] = task_data.get(
            "family", f"{service_td.data['family']}-tasks"
        )
        # Remove any portMappings fro our task definition -- we don't need them
        # for ephemeral tasks
        for container in base_td.containers:
            if "portMappings" in container.data:
                del container.data["portMappings"]
        # Automatically set our networkMode
        if "networkConfiguration" in data_base:
            # We need awsvpc network mode, because we have VPC configuration
            base_td.data["networkMode"] = "awsvpc"
        else:
            base_td.data["networkMode"] = "bridge"
        return data_base, base_td

    def _preprocess_task_data(self, task_data: dict[str, Any]) -> None:
        """
        Change old style command defintions that look like this:

            tasks:
              - family: foobar-test-helper
                environment: test
                network_mode: bridge
                task_role_arn: ${terraform.iam_task_role}
                containers:
                  - name: foobar
                    image: ${terraform.ecr_repo_url}:0.1.0
                    cpu: 128
                    memory: 384
                    commands:
                      migrate: ./manage.py migrate
                      update_index: ./manage.py update_index

        to look like this:

            tasks:
              - family: foobar-test-helper
                environment: test
                network_mode: bridge
                task_role_arn: ${terraform.iam_task_role}
                containers:
                  - name: foobar
                    image: ${terraform.ecr_repo_url}:0.1.0
                    cpu: 128
                  memory: 384
                commands:
                  - name: migrate
                    containers:
                      - name: foobar
                        command: ./manage.py migrate
                  - name: update_index
                    containers:
                      - name: foobar
                        command: ./manage.py update_index

        Args:
            task_data: task data.

        """
        if "containers" in task_data:
            for container_data in task_data["containers"]:
                if "commands" in container_data:
                    if "commands" not in task_data:
                        task_data["commands"] = []
                    for command_name, command in list(
                        container_data["commands"].items()
                    ):
                        task_data["commands"].append(
                            {
                                "name": command_name,
                                "containers": [
                                    {"name": container_data["name"], "command": command}
                                ],
                            }
                        )
                    del container_data["commands"]

    def _get_command_specific_data(  # noqa: D417
        self,
        command_data: dict[str, Any],
        data_base: dict[str, Any],
        base_td: TaskDefinition,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Build a dict that takes info from the output of
        :py:meth:`_get_base_task_data` and overlays the command specific task data
        to build the parameters we'll need when running the task.  Also build a
        new TaskDefinition object that is the TaskDefinition returned by
        :py:meth:`_get_base_task_data` overlaid with the changes from the command
        specific task data.

        Args:
            commmand: the command specific task data
            data_base: the dict returned by self._get_base_task_data()
            service_td: the TaskDefinition object returned by self._get_base_task_data()

        Returns:
            A 2-tuple: dict of parameters for the factory method of
            :py:class:`deployfish.core.models.ecs.ServiceHelperTask`, and the
            new TaskDefinition object

        """
        data: dict[str, Any] = {}
        kwargs: dict[str, Any] = {}
        # Build our new Task data based on the general task overlay we got from
        # :py:meth:`_get_base_task_data`
        self.get_data(data, command_data, source=data_base)
        data["service"] = self.service.pk
        if "cluster" not in data:
            data["cluster"] = self.service.data["cluster"]
        try:
            data["name"] = command_data["name"]
        except KeyError:
            msg = (
                f'Service(pk="{self.service.pk}"): Each helper task must have a '
                '"name" assigned in the "commands" section'
            )
            raise self.SchemaException(msg) from None
        if "family" not in command_data:
            # Make the task definition family be named after our command
            command_name = command_data["name"].replace("_", "-")
            command_data["family"] = f"{base_td.data['family']}-{command_name}"
        # Generate our overlay task definition
        command_td_overlay = TaskDefinition.new(
            command_data, "deployfish", partial=True
        )
        # Use that to make our actual task definition
        command_td = base_td + command_td_overlay
        # Update the deployfish specific environment variables in our task
        # definition's containers
        self.update_container_environments(
            command_td,
            {
                "DEPLOYFISH_TASK_NAME": command_data["family"],
                "DEPLOYFISH_CLUSTER_NAME": data["cluster"],
                "DEPLOYFISH_ENVIRONMENT": self.service.deployfish_environment,
            },
        )
        kwargs["task_definition"] = command_td
        # See if we need to schedule this command
        if "schedule" in command_data:
            if "schedule_role" not in data:
                msg_0 = (
                    f'ServiceHelperTask("{command_data["name"]}") in '
                    f'Service("{self.service.pk}"): "schedule_role" is required '
                    "when you specify a schedule"
                )
                raise self.SchemaException(msg_0)
            kwargs["schedule"] = EventScheduleRule.new(
                self.get_schedule_data(data, command_td), "deployfish"
            )
        return data, kwargs

    def convert(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Convert.

        Returns:
            Operation result.

        """
        data_list = []
        kwargs_list = []
        service_td = self.service.task_definition.copy()
        if "tasks" in self.data:
            for task in self.data["tasks"]:
                # Preprocess the data to turn the old-style command definitions
                # into the new style definitions
                self._preprocess_task_data(task)
                data_base, base_td = self._get_base_task_data(task, service_td)
                # Now iterate through each item in task -> commands
                for command in task["commands"]:
                    command_data, command_kwargs = self._get_command_specific_data(
                        command, data_base, base_td
                    )
                    self.update_container_logging(
                        command_data, command_kwargs["task_definition"]
                    )
                    data_list.append(command_data)
                    kwargs_list.append(command_kwargs)
        return data_list, kwargs_list
