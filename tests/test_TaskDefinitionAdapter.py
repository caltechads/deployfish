from copy import deepcopy

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.adapters.deployfish.ecs import TaskDefinitionAdapter
from deployfish.core.models import Secret

from tests.fixtures import SERVICE_YML


class TestTaskDefinitionAdapter:
    def test_convert_produces_registerable_payload(self) -> None:
        adapter = TaskDefinitionAdapter(deepcopy(SERVICE_YML))
        data, kwargs = adapter.convert()
        assert data["family"] == "foobar-test"
        assert data["networkMode"] == "host"
        assert data["taskRoleArn"] == "MY_TASK_ROLE_ARN"
        assert data["executionRoleArn"] == "MY_EXECUTION_ROLE_ARN"
        assert len(kwargs["containers"]) == 1
        container_data = kwargs["containers"][0][0]
        assert container_data["name"] == "foobar"
        assert container_data["image"] == "foobar/foobar:0.1.0"

    def test_convert_with_secrets_and_extra_environment(self) -> None:
        secrets = [
            Secret.new({"value": "DEBUG=False"}, "deployfish", cluster="c", name="s"),
        ]
        adapter = TaskDefinitionAdapter(
            deepcopy(SERVICE_YML),
            secrets=secrets,
            extra_environment={"DEPLOYFISH_SERVICE_NAME": "foobar-test"},
        )
        data, kwargs = adapter.convert()
        container_data = kwargs["containers"][0][0]
        env_names = {entry["name"] for entry in container_data["environment"]}
        assert "DEPLOYFISH_SERVICE_NAME" in env_names

    def test_fargate_requires_execution_role(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["launch_type"] = "FARGATE"
        del data["execution_role"]
        adapter = TaskDefinitionAdapter(data)
        with pytest.raises(KeyError):
            adapter.convert()

    def test_fargate_sets_requires_compatibilities(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["launch_type"] = "FARGATE"
        adapter = TaskDefinitionAdapter(data)
        payload, _kwargs = adapter.convert()
        assert payload["requiresCompatibilities"] == ["FARGATE"]
