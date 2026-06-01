"""ServiceManager update/save/scale coverage."""

from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.models.ecs import Cluster, Service

from tests.fixtures import SERVICE_YML

SERVICE_DATA = {
    "serviceName": "foobar-test",
    "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
    "status": "ACTIVE",
    "taskDefinition": "arn:aws:ecs:us-west-2:123:task-definition/foobar-test:1",
    "desiredCount": 1,
    "runningCount": 1,
}


class TestServiceManagerListValidation:
    def test_list_invalid_launch_type(self) -> None:
        with pytest.raises(Service.OperationFailed, match="launch_type"):
            Service.objects.list(launch_type="BAD")


class TestServiceManagerUpdateSave:
    def test_update_calls_client(self, _mock_boto3_session: MagicMock) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        service.data["taskDefinition"] = SERVICE_DATA["taskDefinition"]
        service.data["enableExecuteCommand"] = False
        with (
            patch.object(Service.objects, "exists", return_value=True),
            patch.object(
                service,
                "render_for_update",
                return_value={"cluster": "foobar-cluster", "service": "foobar-test"},
            ),
        ):
            Service.objects.update(service)
        _mock_boto3_session.update_service.assert_called_once()

    def test_update_raises_when_service_missing(self) -> None:
        service = Service(SERVICE_DATA)
        service.data["cluster"] = "foobar-cluster"
        with patch.object(Service.objects, "exists", return_value=False):
            with pytest.raises(Service.DoesNotExist):
                Service.objects.update(service)

    def test_update_raises_when_not_active(
        self, _mock_boto3_session: MagicMock
    ) -> None:
        service = Service(SERVICE_DATA)
        service.data["cluster"] = "foobar-cluster"
        exc = type("ServiceNotActiveException", (Exception,), {})
        _mock_boto3_session.exceptions.ServiceNotActiveException = exc
        _mock_boto3_session.update_service.side_effect = exc("inactive")
        with (
            patch.object(Service.objects, "exists", return_value=True),
            patch.object(service, "render_for_update", return_value={}),
            pytest.raises(Service.OperationFailed),
        ):
            Service.objects.update(service)

    def test_save_creates_when_missing(self, _mock_boto3_session: MagicMock) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        with (
            patch.object(Service.objects, "exists", return_value=False),
            patch.object(Service.objects, "create") as create_mock,
        ):
            Service.objects.save(service)
        create_mock.assert_called_once_with(service)

    def test_save_updates_when_exists(self) -> None:
        service = Service(SERVICE_DATA)
        service.data["cluster"] = "foobar-cluster"
        with (
            patch.object(Service.objects, "exists", return_value=True),
            patch.object(Service.objects, "update") as update_mock,
        ):
            Service.objects.save(service)
        update_mock.assert_called_once()

    def test_scale_calls_update_service(self, _mock_boto3_session: MagicMock) -> None:
        service = Service(SERVICE_DATA)
        service.data["cluster"] = "foobar-cluster"
        with patch.object(
            service, "render_for_scale", return_value={"desiredCount": 5}
        ):
            Service.objects.scale(service, 5)
        _mock_boto3_session.update_service.assert_called_once()

    def test_get_raises_cluster_not_found(self, _mock_boto3_session: MagicMock) -> None:
        exc = type("ClusterNotFoundException", (Exception,), {})
        _mock_boto3_session.exceptions.ClusterNotFoundException = exc
        _mock_boto3_session.describe_services.side_effect = exc("missing")
        with pytest.raises(Cluster.DoesNotExist):
            Service.objects.get("missing:foobar-test")
