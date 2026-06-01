from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.models.ecs import Service, StandaloneTask

from tests.fixtures import SERVICE_YML, STANDALONE_TASK_YML


def _service() -> Service:
    service = Service.new(deepcopy(SERVICE_YML), "deployfish")
    service.data["cluster"] = "foobar-cluster"
    service.data["serviceName"] = "foobar-test"
    service.appscaling = None
    return service


class TestServiceManagerSaveUpdate:
    def test_save_creates_when_missing(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        service = _service()
        with patch.object(Service.objects, "exists", return_value=False):
            with patch.object(
                service, "render_for_create", return_value={"cluster": "foobar-cluster"}
            ):
                Service.objects.save(service)
        client.create_service.assert_called_once()

    def test_save_updates_when_exists(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        service = _service()
        with patch.object(Service.objects, "exists", return_value=True):
            with patch.object(
                service, "render_for_update", return_value={"cluster": "foobar-cluster"}
            ):
                Service.objects.save(service)
        client.update_service.assert_called_once()

    def test_create_raises_when_cluster_missing(
        self, _mock_boto3_session: MagicMock
    ) -> None:
        client = _mock_boto3_session
        exc = type("ClusterNotFoundException", (Exception,), {})
        client.exceptions.ClusterNotFoundException = exc
        client.create_service.side_effect = exc("missing")
        service = _service()
        with patch.object(Service.objects, "exists", return_value=False):
            with patch.object(service, "render_for_create", return_value={}):
                with pytest.raises(Exception):
                    Service.objects.create(service)

    def test_list_invalid_launch_type(self) -> None:
        with pytest.raises(Service.OperationFailed):
            Service.objects.list(launch_type="INVALID")

    def test_list_invalid_scheduling_strategy(self) -> None:
        with pytest.raises(Service.OperationFailed):
            Service.objects.list(scheduling_strategy="INVALID")


class TestStandaloneTaskSave:
    def test_save_registers_task_definition(
        self, _mock_boto3_session: MagicMock
    ) -> None:
        from deployfish.core.models.events import EventScheduleRule

        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        with patch.object(
            task.task_definition, "save", return_value="arn:task-def:new"
        ) as save_mock:
            with patch.object(
                EventScheduleRule.objects,
                "get",
                side_effect=EventScheduleRule.DoesNotExist("none"),
            ):
                arn = StandaloneTask.objects.save(task)
        save_mock.assert_called_once()
        assert arn == "arn:task-def:new"

    def test_delete_unschedules_task(self, _mock_boto3_session: MagicMock) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        with (
            patch(
                "deployfish.core.models.ecs.EventScheduleRule.objects.exists",
                return_value=True,
            ),
            patch(
                "deployfish.core.models.ecs.EventScheduleRule.objects.delete",
            ) as delete_mock,
        ):
            StandaloneTask.objects.delete(task)
        delete_mock.assert_called_once()
