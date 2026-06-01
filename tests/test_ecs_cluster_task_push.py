"""Additional ECS Service manager coverage."""

from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.ecs import Service

from tests.fixtures import SERVICE_YML


class TestServiceManagerCreate:
    def test_create_calls_client(self, _mock_boto3_session: MagicMock) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        with (
            patch.object(Service.objects, "exists", return_value=False),
            patch.object(
                service,
                "render_for_create",
                return_value={
                    "cluster": "foobar-cluster",
                    "serviceName": "foobar-test",
                },
            ),
        ):
            Service.objects.create(service)
        _mock_boto3_session.create_service.assert_called_once()

    def test_create_skips_when_already_exists(
        self, _mock_boto3_session: MagicMock
    ) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        with patch.object(Service.objects, "exists", return_value=True):
            Service.objects.create(service)
        _mock_boto3_session.create_service.assert_not_called()
