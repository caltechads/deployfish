from copy import deepcopy

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.adapters import ServiceAdapter
from deployfish.core.models.appscaling import ScalableTarget
from deployfish.core.models.ecs import TaskDefinition

from tests.fixtures import APPLICATION_SCALING_YML, FARGATE_SERVICE_YML, SERVICE_YML


class TestServiceAdapter:
    def test_get_client_token_truncates_to_35_chars(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["name"] = "a-very-long-service-name-that-exceeds-limits"
        adapter = ServiceAdapter(data)
        assert len(adapter.get_clientToken()) <= 35
        assert adapter.get_clientToken().startswith("token-")

    def test_get_task_definition_includes_deployfish_env(self) -> None:
        adapter = ServiceAdapter(deepcopy(SERVICE_YML))
        task_def = adapter.get_task_definition()
        assert isinstance(task_def, TaskDefinition)
        environment = task_def.containers[0].data["environment"]
        env_names = {entry["name"] for entry in environment}
        assert "DEPLOYFISH_SERVICE_NAME" in env_names
        assert "DEPLOYFISH_ENVIRONMENT" in env_names
        assert "DEPLOYFISH_CLUSTER_NAME" in env_names

    def test_get_load_balancers_single_target_group(self) -> None:
        adapter = ServiceAdapter(deepcopy(SERVICE_YML))
        load_balancers = adapter.get_loadBalancers()
        assert load_balancers == [
            {
                "targetGroupArn": "MY_TARGET_GROUP_ARN",
                "containerName": "foobar",
                "containerPort": 8080,
            }
        ]

    def test_get_load_balancers_multiple_target_groups(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["load_balancer"]["target_groups"].append(
            {
                "target_group_arn": "MY_TARGET_GROUP_ARN_2",
                "container_name": "foobar",
                "container_port": 9090,
            }
        )
        adapter = ServiceAdapter(data)
        assert len(adapter.get_loadBalancers()) == 2

    def test_get_load_balancers_classic_elb(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["load_balancer"] = {
            "load_balancer_name": "my-elb",
            "container_name": "foobar",
            "container_port": 80,
        }
        adapter = ServiceAdapter(data)
        assert adapter.get_loadBalancers() == [
            {
                "loadBalancerName": "my-elb",
                "containerName": "foobar",
                "containerPort": 80,
            }
        ]

    def test_convert_includes_application_scaling(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["application_scaling"] = deepcopy(APPLICATION_SCALING_YML)
        adapter = ServiceAdapter(data)
        _service_data, kwargs = adapter.convert()
        assert "appscaling" in kwargs
        assert isinstance(kwargs["appscaling"], ScalableTarget)
        assert kwargs["appscaling"].data["MinCapacity"] == 2
        assert kwargs["appscaling"].data["MaxCapacity"] == 4

    def test_convert_without_application_scaling(self) -> None:
        adapter = ServiceAdapter(deepcopy(SERVICE_YML))
        _service_data, kwargs = adapter.convert()
        assert "appscaling" not in kwargs

    def test_convert_fargate_rejects_autoscalinggroup_name(self) -> None:
        data = deepcopy(FARGATE_SERVICE_YML)
        data["autoscalinggroup_name"] = "my-asg"

        with pytest.raises(
            ServiceAdapter.SchemaException,
            match=r"autoscalinggroup_name.*EC2-only.*FARGATE.*application_scaling",
        ):
            ServiceAdapter(data).convert()

    def test_convert_fargate_omits_autoscalinggroup_name(self) -> None:
        data = deepcopy(FARGATE_SERVICE_YML)
        adapter = ServiceAdapter(data)

        _service_data, kwargs = adapter.convert()

        assert "autoscalinggroup_name" not in kwargs

    def test_load_secrets_false_skips_secrets(self) -> None:
        adapter = ServiceAdapter(deepcopy(SERVICE_YML), load_secrets=False)
        task_def = adapter.get_task_definition()
        assert task_def.secrets == {}
