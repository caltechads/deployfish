from typing import Any

from deployfish.config import get_config
from deployfish.core.models import EventScheduleRule, TaskDefinition
from deployfish.core.models.secrets import Secret

from ..secrets import SecretsMixin
from .common import AbstractTaskAdapter


class StandaloneTaskAdapter(SecretsMixin, AbstractTaskAdapter):
    """
    Model standalone task adapter behavior.
    """

    def get_task_definition(
        self, secrets: list[Secret] | None = None
    ) -> TaskDefinition:
        """
        Get task definition.

        Args:
            secrets: secrets.

        Returns:
            Operation result.

        """
        deployfish_environment = {
            "DEPLOYFISH_TASK_NAME": self.data["name"],
            "DEPLOYFISH_ENVIRONMENT": self.data.get("environment", "undefined"),
            "DEPLOYFISH_CLUSTER_NAME": self.data["cluster"],
        }
        return TaskDefinition.new(
            self.data,
            "deployfish",
            secrets=secrets,
            extra_environment=deployfish_environment,
        )

    def convert(self) -> tuple[dict[str, Any], dict[str, Any]]:  # noqa: PLR0912, PLR0915
        """
        Convert.

        Returns:
            Operation result.

        """
        data: dict[str, Any] = {}
        data["name"] = self.data["name"]
        if "family" not in self.data:
            self.data["family"] = data["name"]
        if "service" in self.data:
            # We actually want the Service.pk here, not just the bare service
            # name, but in deployfish.yml we've allowed people to just name the
            # bare service of things that are in the same deployfish.yml
            data["service"] = self.data["service"]
            if ":" not in data["service"]:
                config = get_config()
                # This is not a Service.pk
                try:
                    service_data = config.get_section_item("services", data["service"])
                except KeyError as e:
                    msg = 'No service named "{}" exists in deployfish.yml'.format(
                        data["service"]
                    )
                    raise self.SchemaException(msg) from e
                data["service"] = f"{service_data['cluster']}:{service_data['name']}"
        data["cluster"] = self.data.get("cluster", "default")
        vpc_configuration = self.get_vpc_configuration()
        if vpc_configuration:
            data["networkConfiguration"] = {}
            data["networkConfiguration"]["awsvpcConfiguration"] = vpc_configuration
        data["count"] = self.data.get("count", 1)
        data["launchType"] = self.data.get("launch_type", "EC2")
        if data["launchType"] == "FARGATE":
            data["platformVersion"] = self.data.get("platform_version", "LATEST")
        if self.data.get("runtime_platform", None):
            data["runtimePlatform"] = {}
            data["runtimePlatform"]["cpuArchitecture"] = self.data[
                "runtime_platform"
            ].get("cpu_architecture", "X86_64")
            data["runtimePlatform"]["operatingSystemFamily"] = self.data[
                "runtime_platform"
            ].get("operating_system_family", "LINUX")
        elif "capacity_provider_strategy" in self.data:
            data["capacityProviderStrategy"] = self.data["capacity_provider_strategy"]
        if "placement_constraints" in self.data:
            data["placementConstraints"] = self.data["placement_constraints"]
        if "placement_strategy" in self.data:
            data["placementStrategy"] = self.data["placement_strategy"]
        if "group" in self.data:
            data["Group"] = self.data["group"]
        if "count" in self.data:
            data["count"] = self.data["count"]
        kwargs: dict[str, Any] = {}
        secrets: list[Secret] = []
        if "config" in self.data:
            secrets = self.get_secrets(
                data["cluster"], f"task-{data['name']}", decrypt=False
            )
        kwargs["task_definition"] = self.get_task_definition(secrets=secrets)
        self.update_container_logging(data, kwargs["task_definition"])
        if (
            "networkConfiguration" in data
            and kwargs["task_definition"].data["networkMode"] != "awsvpc"
        ):
            kwargs["task_definition"].data["networkMode"] = "awsvpc"
        if "schedule" in self.data:
            data["schedule"] = self.data["schedule"]
            if "schedule_role" in self.data:
                data["schedule_role"] = self.data["schedule_role"]
            if "schedule_role" not in data:
                msg_0 = (
                    f'StandaloneTask("{data["name"]}"): "schedule_role" is required '
                    "when you specify a schedule"
                )
                raise self.SchemaException(msg_0) from None
            kwargs["schedule"] = EventScheduleRule.new(
                self.get_schedule_data(data, kwargs["task_definition"]), "deployfish"
            )
        return data, kwargs
