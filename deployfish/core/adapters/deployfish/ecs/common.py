import os
from typing import Any, cast

from deployfish.core.aws import get_boto3_session
from deployfish.core.models import TaskDefinition

from ...abstract import Adapter

# ------------------------
# Mixins
# ------------------------


class VpcConfigurationMixin:
    """
    Model vpc configuration mixin behavior.
    """

    #: Data.
    data: dict[str, Any]

    def get_vpc_configuration(
        self, source: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Get vpc configuration.

        Args:
            source: source.

        Returns:
            Operation result.

        """
        data: dict[str, Any] = {}
        if not source:
            source = self.data.get("vpc_configuration", None)
        if source:
            data["subnets"] = source["subnets"]
            if "security_groups" in source:
                data["securityGroups"] = source["security_groups"]
            if "public_ip" in source:
                data["assignPublicIp"] = source["public_ip"]
            else:
                data["assignPublicIp"] = "DISABLED"
        return data


# ------------------------
# Abstract Adapters
# ------------------------


class AbstractTaskAdapter(VpcConfigurationMixin, Adapter):
    """
    Model abstract task adapter behavior.
    """

    def is_fargate(self, _: dict[str, Any]) -> bool:
        """
        Return ``True ``if this task definition is for FARGATE, ``False``
        otherwise.

        Args:
            _: .

        Returns:
            Operation result.

        """
        return bool(
            "requiresCompatibilities" in self.data
            and self.data["requiresCompatibilities"] == ["FARGATE"]
        )

    def get_schedule_data(
        self, data: dict[str, Any], task_definition: TaskDefinition
    ) -> dict[str, Any]:
        """
        Construct the dict that will be given as input for configuring an
        :py:class:`deployfish.core.models.events.EventScheduleRule` and
        :py:class:`deployfish.core.models.events.EventTarget` for our helper task.

        The :py:meth:`deployfish.core.models.events.EventScheduleRule.new`
        factory method expects this struct::

            {
                'name': the name for the schedule
                'schedule': the schedule expression
                'schedule_role': the ARN of the role EventBridge will use to execute our
                task definition
                'cluster': the name of the cluster in which to run our tasks
                'count': (optional) the number of tasks to run
                'launch_type': (optional): "FARGATE" or "EC2"
                'platform_version': (optional)
                'group': (optional) task group
                'vpc_configuration': { (optional)
                'subnets': list of subnet ids
                'security_groups': list of security group ids
                'public_ip': bool: assign a public ip to our containers?
                }
            }

        Args:
            data: The output of :py:meth:`get_data`
            task_definition: The task definition to schedule

        Returns:
            Data appropriate for configuring an ``EventScheduleRule`` and
            ``EventTarget``

        """
        schedule_data: dict[str, Any] = {}
        schedule_data["name"] = task_definition.data["family"]
        schedule_data["schedule"] = data["schedule"]
        if "schedule_role" in data:
            schedule_data["schedule_role"] = data["schedule_role"]
        schedule_data["cluster"] = data["cluster"]
        if "count" not in schedule_data:
            schedule_data["count"] = 1
        if "launchType" in data:
            schedule_data["launch_type"] = data["launchType"]
        if schedule_data.get("launch_type", "EC2") == "FARGATE":
            if "platformVersion" in data:
                schedule_data["platform_version"] = data["platformVersion"]
        if "group" in data:
            schedule_data["group"] = data["group"]
        if "networkConfiguration" in data:
            vc = data["networkConfiguration"]["awsvpcConfiguration"]
            schedule_data["vpc_configuration"] = {}
            if "subnets" in vc:
                schedule_data["vpc_configuration"]["subnets"] = vc["subnets"]
            if "securityGroups" in vc:
                schedule_data["vpc_configuration"]["security_groups"] = vc[
                    "securityGroups"
                ]
            if "allowPublicIp" in vc:
                schedule_data["vpc_configuration"]["public_ip"] = (
                    vc["allowPublicIp"] == "ENABLED"
                )
        return schedule_data

    def update_container_logging(
        self, data: dict[str, Any], task_definition: TaskDefinition
    ) -> None:
        """
        When creating :py:class:`deployfish.core.models.ecs.ServiceHelperTask`
        objects, from a ``deployfish.yml`` service definition, we always create
        the tasks as FARGATE tasks.  To make a ``ServiceHelperTask``, we copy
        the service's task definition and modify it to be a FARGATE task as well
        as with the appropriate overrides from the ``tasks:`` section of the
        service definition.

        However, the service itself may be an EC2 based task.  If so, we may not
        be able to use the same logging configuration for the tasks as we do for
        the service.  This is because FARGATE tasks can only use these logging
        drivers: ``awslogs``, ``splunk``, ``awsfirelens``, while EC2 services
        and tasks have a much longer list of supported logging drivers (e.g.
        ``fluentd``).

        Or, we may not have a logging configuration at all for the service or
        task we want, in which case we need to add one.

        Examine each container in our task definition and if

        * there is no logging stanza at all for the container
        * or the logging driver is not valid for FARGATE

        replace the logging stanza with one that writes the logs to ``awslogs``.

        We'll set the log group to be either ``/<cluster>/<service>`` or
        ``/<cluster>/standalone-tasks`` depending on whether this is a
        ``ServiceHelperTask`` or a ``StandaloneTask``, and set the log
        strem prefix to that of our name

        Args:
            data: the data dict for the container
            task_definition: the
                :py:class:`deployfish.core.models.ecs.TaskDefinition` object that
                owns this container

        """
        if task_definition.is_fargate():
            for container in task_definition.containers:
                if "logConfiguration" in container.data:
                    lc = container.data["logConfiguration"]
                    if lc["logDriver"] in ["awslogs", "splunk", "awsfirelens"]:
                        continue
                # the log configuration needs to be fixed
                try:
                    region_name: str = cast("str", get_boto3_session().region_name)
                except AttributeError:
                    region_name = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
                if "service" in data:
                    log_group = "/{}/{}".format(*data["service"].split(":"))
                else:
                    log_group = f"/{data['cluster']}/standalone-tasks"
                lc = {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-create-group": "true",
                        "awslogs-region": region_name,
                        "awslogs-group": log_group,
                        "awslogs-stream-prefix": data["name"],
                    },
                }
                container.data["logConfiguration"] = lc
