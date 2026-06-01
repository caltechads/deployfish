from copy import deepcopy
from unittest.mock import patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.ecs import ContainerDefinition, Service, TaskDefinition

from tests.fixtures import FARGATE_SERVICE_YML, SERVICE_YML, SERVICE_YML_WITH_SCALING


def _aws_service(yml: dict | None = None) -> Service:
    service = Service.new(deepcopy(yml or SERVICE_YML), "deployfish")
    service.data["cluster"] = "foobar-cluster"
    service.data["serviceName"] = "foobar-test"
    service.data["desiredCount"] = 1
    service.data["runningCount"] = 1
    service.data["pendingCount"] = 0
    service.appscaling = None
    return service


class TestServiceRenderMethods:
    def test_render_for_scale_sets_count(self) -> None:
        service = _aws_service()
        payload = service.render_for_scale(5)
        assert payload["desiredCount"] == 5
        assert payload["cluster"] == "foobar-cluster"

    def test_render_tags_from_service_tags(self) -> None:
        service = _aws_service()
        service._tags = {"Environment": "prod"}
        tags = service.render_tags()
        assert tags == [{"key": "Environment", "value": "prod"}]

    def test_scale_delegates_to_manager(self) -> None:
        service = _aws_service()
        with patch.object(Service.objects, "scale") as scale_mock:
            service.scale(2)
        scale_mock.assert_called_once_with(service, 2)


class TestFargateServiceProperties:
    def test_fargate_launch_type(self) -> None:
        service = Service.new(deepcopy(FARGATE_SERVICE_YML), "deployfish")
        assert service.launch_type == "FARGATE"

    def test_service_with_scaling_has_appscaling(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML_WITH_SCALING), "deployfish")
        assert service.appscaling is not None
        assert service.appscaling.data["MinCapacity"] == 2


class TestTaskDefinitionProperties:
    def test_task_definition_containers_list(self) -> None:
        service = _aws_service()
        assert len(service.task_definition.containers) == 1
        assert isinstance(service.task_definition.containers[0], ContainerDefinition)

    def test_task_definition_family(self) -> None:
        service = _aws_service()
        assert service.task_definition.family == "foobar-test"

    def test_task_definition_render(self) -> None:
        td = TaskDefinition(
            {"family": "app", "revision": 2, "taskDefinitionArn": "arn:1"},
            containers=[],
        )
        rendered = td.render()
        assert rendered["family"] == "app"
