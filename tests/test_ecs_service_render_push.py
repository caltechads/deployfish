"""Coverage for Service render/save paths and related model branches."""

import warnings
from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.ecs import Service

from tests.fixtures import FARGATE_SERVICE_YML, SERVICE_YML, SERVICE_YML_WITH_SCALING


def _service_from_yml(yml: dict | None = None) -> Service:
    service = Service.new(deepcopy(yml or SERVICE_YML), "deployfish")
    service.data["cluster"] = "foobar-cluster"
    service.data["serviceName"] = "foobar-test"
    return service


def _service_from_aws() -> Service:
    return Service(
        {
            "serviceName": "foobar-test",
            "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
            "cluster": "foobar-cluster",
            "status": "ACTIVE",
            "taskDefinition": "arn:aws:ecs:us-west-2:123:task-definition/foobar-test:1",
            "desiredCount": 2,
            "runningCount": 2,
            "pendingCount": 0,
            "createdAt": "2025-01-01T00:00:00Z",
            "serviceArn": "arn:aws:ecs:us-west-2:123:service/foobar-cluster/foobar-test",
            "events": [{"message": "steady"}],
            "deployments": [{"status": "PRIMARY", "createdAt": "2025-01-01T00:00:00Z"}],
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": ["subnet-b", "subnet-a"],
                    "securityGroups": ["sg-b", "sg-a"],
                }
            },
        }
    )


class TestServiceRenderForDisplay:
    def test_render_for_display_from_deployfish_yml(self) -> None:
        service = _service_from_yml()
        service.data["role"] = "arn:aws:iam::123:role/ecs"
        with patch.object(
            service.task_definition,
            "render_for_display",
            return_value={"family": "foobar-test"},
        ):
            display = service.render_for_display()
        assert display["status"] == "ACTIVE"
        assert display["roleArn"] == "arn:aws:iam::123:role/ecs"
        assert "role" not in display
        assert display["serviceArn"] == "NONE"

    def test_render_for_display_includes_appscaling_and_discovery(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML_WITH_SCALING), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        service.service_discovery = MagicMock()
        service.service_discovery.render_for_display.return_value = {"Name": "api"}
        with patch.object(
            service.task_definition,
            "render_for_display",
            return_value={"family": "foobar-test"},
        ):
            display = service.render_for_display()
        assert "appscaling" in display
        assert display["service_discovery"] == {"Name": "api"}


class TestServiceRenderForDiff:
    def test_render_for_diff_from_yml_adds_defaults(self) -> None:
        service = _service_from_yml()
        service.data["role"] = "arn:aws:iam::123:role/ecs"
        diff = service.render_for_diff()
        assert diff["status"] == "ACTIVE"
        assert diff["healthCheckGracePeriodSeconds"] == 0

    def test_render_for_diff_from_aws_strips_ephemeral(self) -> None:
        service = _service_from_aws()
        td = MagicMock()
        td.render_for_diff.return_value = {"family": "foobar-test"}
        service.cache["task_definition"] = td
        diff = service.render_for_diff()
        assert "serviceArn" not in diff
        assert "events" not in diff
        subnets = diff["networkConfiguration"]["awsvpcConfiguration"]["subnets"]
        assert subnets == ["subnet-a", "subnet-b"]

    def test_render_for_diff_unknown_status_from_yml(self) -> None:
        service = _service_from_yml()
        diff = service.render_for_diff()
        assert diff["status"] == "(known after save)"


class TestServiceRenderForUpdate:
    def test_render_for_update_includes_load_balancers_for_alb(self) -> None:
        service = _service_from_yml()
        service.data["loadBalancers"] = [{"targetGroupArn": "arn:tg:1"}]
        service.data["enableExecuteCommand"] = True
        service.data["taskDefinition"] = "arn:td:1"
        payload = service.render_for_update()
        assert payload["loadBalancers"] == service.data["loadBalancers"]

    def test_render_for_update_warns_on_classic_lb(self) -> None:
        service = _service_from_yml()
        service.data["loadBalancers"] = [{"loadBalancerName": "classic-lb"}]
        service.data["enableExecuteCommand"] = False
        service.data["taskDefinition"] = "arn:td:1"
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            payload = service.render_for_update()
        assert "loadBalancers" not in payload
        assert len(caught) == 1

    def test_render_for_update_fargate_platform_version(self) -> None:
        service = Service.new(deepcopy(FARGATE_SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        service.data["launchType"] = "FARGATE"
        service.data["taskDefinition"] = "arn:td:1"
        service.data["enableExecuteCommand"] = True
        payload = service.render_for_update()
        assert payload["platformVersion"] == "LATEST"


class TestServiceSaveFlow:
    def test_save_updates_discovery_and_appscaling(self) -> None:
        service = _service_from_yml()
        existing = MagicMock()
        existing.service_discovery = MagicMock()
        existing.appscaling = MagicMock()
        service.service_discovery = MagicMock()
        service.service_discovery.save.return_value = "arn:registry:1"
        service.appscaling = MagicMock()
        helper = MagicMock()
        helper.save.return_value = "arn:helper:1"
        service.helper_tasks = [helper]
        with (
            patch.object(Service.objects, "get", return_value=existing),
            patch.object(service.task_definition, "save", return_value="arn:td:2"),
            patch("deployfish.core.models.abstract.Model.save"),
        ):
            service.save()
        service.service_discovery.save.assert_called_once()
        service.appscaling.save.assert_called_once()
        assert service.data["serviceRegistries"] == [{"registryArn": "arn:registry:1"}]

    def test_save_removes_existing_service_discovery(self) -> None:
        service = _service_from_yml()
        service.service_discovery = None
        existing = MagicMock()
        existing.service_discovery = MagicMock()
        with (
            patch.object(Service.objects, "get", return_value=existing),
            patch.object(service.task_definition, "save", return_value="arn:td:1"),
            patch("deployfish.core.models.abstract.Model.save"),
        ):
            service.save()
        existing.service_discovery.delete.assert_called_once()

    def test_save_removes_existing_appscaling(self) -> None:
        service = _service_from_yml()
        service.appscaling = None
        existing = MagicMock()
        existing.appscaling = MagicMock()
        with (
            patch.object(Service.objects, "get", return_value=existing),
            patch.object(service.task_definition, "save", return_value="arn:td:1"),
            patch("deployfish.core.models.abstract.Model.save"),
        ):
            service.save()
        existing.appscaling.delete.assert_called_once()


class TestServiceProperties:
    def test_containers_status_exec_environment(self) -> None:
        service = _service_from_yml()
        service.data["enableExecuteCommand"] = True
        service.data["status"] = "ACTIVE"
        service._tags = {"deployfish:Environment": "prod"}
        assert service.exec_enabled is True
        assert service.status == "ACTIVE"
        assert service.deployfish_environment == "prod"
        assert len(service.containers) == 1

    def test_service_new_sets_optional_kwargs(self) -> None:
        from tests.fixtures import SERVICE_YML_WITH_HELPER_TASKS

        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        assert len(service.helper_tasks) >= 1
