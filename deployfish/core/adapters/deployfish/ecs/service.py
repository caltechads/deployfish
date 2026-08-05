from typing import Any

from deployfish.core.models import (
    ScalableTarget,
    ServiceDiscoveryService,
    TaskDefinition,
)
from deployfish.core.models.secrets import Secret

from ...abstract import Adapter
from ..mixins import SSHConfigMixin
from ..secrets import SecretsMixin
from .common import VpcConfigurationMixin


class ServiceAdapter(SSHConfigMixin, SecretsMixin, VpcConfigurationMixin, Adapter):
    """
    * Service itself             [x]

    Args:
        data: data.

    """

    def __init__(self, data: dict[str, Any], **kwargs):
        #: Load secrets.
        """
        Initialize ServiceAdapter.

        Args:
            data: data.

        Keyword Args:
            kwargs: kwargs.

        """
        #: Load secrets.
        self.load_secrets: bool = kwargs.pop("load_secrets", True)
        super().__init__(data, **kwargs)

    def get_clientToken(self) -> str:  # noqa: N802
        """
        Get client token.

        Returns:
            Operation result.

        """
        return f"token-{self.data['name']}-{self.data['cluster']}"[:35]

    def get_task_definition(self) -> TaskDefinition:
        """
        Get task definition.

        Returns:
            Operation result.

        """
        secrets = self.__build_Secrets()
        deployfish_environment = {
            "DEPLOYFISH_SERVICE_NAME": self.data["name"],
            "DEPLOYFISH_ENVIRONMENT": self.data.get("environment", "undefined"),
            "DEPLOYFISH_CLUSTER_NAME": self.data["cluster"],
        }
        return TaskDefinition.new(
            self.data,
            "deployfish",
            secrets=secrets,
            extra_environment=deployfish_environment,
        )

    def get_loadBalancers(self) -> list[dict[str, Any]]:  # noqa: N802
        """
        Get load balancers.

        Returns:
            Operation result.

        """
        loadBalancers = []  # noqa: N806
        if "target_groups" in self.data["load_balancer"]:
            # If we want the service to register itself with multiple target
            # groups, the "load_balancer" section will have a list entry named
            # "target_groups".  Each item in the target_group_list will be a
            # dict with keys "target_group_arn", "container_name" and
            # "container_port"
            for group in self.data["load_balancer"]["target_groups"]:
                lb_data = {
                    "targetGroupArn": group["target_group_arn"],
                    "containerName": group["container_name"],
                    "containerPort": int(group["container_port"]),
                }
                loadBalancers.append(lb_data)
        else:
            # We either have just one target group, or we're using an ELB
            group = self.data["load_balancer"]
            if "load_balancer_name" in group:
                # ELB
                loadBalancers.append(
                    {
                        "loadBalancerName": group["load_balancer_name"],
                        "containerName": group["container_name"],
                        "containerPort": int(group["container_port"]),
                    }
                )
            elif "target_group_arn" in self.data["load_balancer"]:
                loadBalancers.append(
                    {
                        "targetGroupArn": group["target_group_arn"],
                        "containerName": group["container_name"],
                        "containerPort": int(group["container_port"]),
                    }
                )
        return loadBalancers

    def __build_Service__data(self, data: dict[str, Any]) -> None:  # noqa: N802, PLR0912
        """
        Update ``data`` with the configuration for the Service itself.  This
        will look like the dict that ``boto3.client('ecs').create_service()``
        needs.

        :rtype: dict(str, *)

        Args:
            data: data.

        """
        data["cluster"] = self.data["cluster"]
        data["serviceName"] = self.data["name"]
        if "load_balancer" in self.data:
            if "service_role_arn" in self.data:
                # backwards compatibility for deployfish.yml < 0.3.6
                data["role"] = self.data["service_role_arn"]
            elif (
                "load_balancer" in self.data
                and "service_role_arn" in self.data["load_balancer"]
            ):
                data["role"] = self.data["load_balancer"]["service_role_arn"]
            data["loadBalancers"] = self.get_loadBalancers()
        if "capacity_provider_strategy" in self.data:
            data["capacityProviderStrategy"] = self.data["capacity_provider_strategy"]
        else:
            # capacity_provider_strategy and launch_type are mutually exclusive
            data["launchType"] = self.data.get("launch_type", "EC2")
            if data["launchType"] == "FARGATE":
                data["platformVersion"] = "LATEST"
        vpc_configuration = self.get_vpc_configuration()
        if vpc_configuration:
            data["networkConfiguration"] = {}
            data["networkConfiguration"]["awsvpcConfiguration"] = vpc_configuration
        if "placement_constraints" in self.data:
            data["placementConstraints"] = self.data["placement_constraints"]
        if "placement_strategy" in self.data:
            data["placementStrategy"] = self.data["placement_strategy"]
        if "healthCheckGracePeriodSeconds" in self.data:
            data["healthCheckGracePeriodSeconds"] = self.data[
                "healthCheckGracePeriodSeconds"
            ]
        data["deploymentConfiguration"] = {}
        data["deploymentConfiguration"]["maximumPercent"] = int(
            self.data.get("maximum_percent", 200)
        )
        data["deploymentConfiguration"]["minimumHealthyPercent"] = int(
            self.data.get("minimum_healthy_percent", 50)
        )
        data["schedulingStrategy"] = self.data.get("scheduling_strategy", "REPLICA")
        if data["schedulingStrategy"] == "DAEMON":
            data["desiredCount"] = "automatically"
            if "deploymentConfiguration" not in data:
                data["deploymentConfiguration"] = {}
            data["deploymentConfiguration"]["maximumPercent"] = 100
        else:
            data["desiredCount"] = self.data["count"]
        data["clientToken"] = self.get_clientToken()
        data["enableExecuteCommand"] = self.data.get("enable_exec", False)
        data["enableECSManagedTags"] = True
        if "propagateTags" in self.data:
            data["propagateTags"] = self.data["propagateTags"]

    def __build_Secrets(self) -> list[Secret]:  # noqa: N802
        """
        Build a list of Secret and ExternalSecret objects from our Service's
        config: section.

        :rtype: list(Union[Secret, ExternalSecret])

        Returns:
            Operation result.

        """
        if self.load_secrets:
            # We only need secret values if we're explicitly showing them
            secrets = self.get_secrets(
                self.data["cluster"], self.data["name"], decrypt=False
            )
        else:
            secrets = []
        return secrets

    def __build_TaskDefinition(self, kwargs: dict[str, Any]) -> None:  # noqa: N802
        """
        Handle build task definition.

        Args:
            kwargs: kwargs.

        """
        kwargs["task_definition"] = self.get_task_definition()

    def __build_application_scaling_objects(self, kwargs: dict[str, Any]) -> None:
        """
        Handle build application scaling objects.

        Args:
            kwargs: kwargs.

        """
        if "application_scaling" in self.data:
            kwargs["appscaling"] = ScalableTarget.new(
                self.data["application_scaling"],
                "deployfish",
                cluster=self.data["cluster"],
                service=self.data["name"],
            )

    def __build_ServiceDiscoveryService(self, kwargs: dict[str, Any]) -> None:  # noqa: N802
        """
        Handle build service discovery service.

        Args:
            kwargs: kwargs.

        """
        if "service_discovery" in self.data:
            if self.data.get("network_mode", "bridge") == "awsvpc":
                kwargs["service_discovery"] = ServiceDiscoveryService.new(
                    self.data["service_discovery"],
                    "deployfish",
                )
            else:
                msg = (
                    'You must use network_mode of "awsvpc" to enable service discovery'
                )
                raise self.SchemaException(msg)

    def __build_tags(self, kwargs: dict[str, Any]) -> None:
        """
        Handle build tags.

        Args:
            kwargs: kwargs.

        """
        tags = {}
        tags["Environment"] = self.data.get("environment", "test")
        kwargs["tags"] = tags

    def convert(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        .. note::

            ServiceHelperTasks are constructed in Service.new(), because

        Returns:
            Operation result.

        """
        data, kwargs = super().convert()
        self.__build_Service__data(data)
        self.__build_TaskDefinition(kwargs)
        self.__build_application_scaling_objects(kwargs)
        self.__build_ServiceDiscoveryService(kwargs)
        self.__build_tags(kwargs)
        if "autoscalinggroup_name" in self.data:
            if data.get("launchType") == "FARGATE":
                msg = (
                    '"autoscalinggroup_name" is EC2-only; do not supply this for '
                    "FARGATE services; use application_scaling instead"
                )
                raise self.SchemaException(msg)
            kwargs["autoscalinggroup_name"] = self.data["autoscalinggroup_name"]
        return data, kwargs
