from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.ecs import Service

from tests.fixtures import SERVICE_YML


class TestServiceManagerExtended:
    def test_scale_updates_desired_count(self, _mock_boto3_session: MagicMock) -> None:
        from copy import deepcopy

        client = _mock_boto3_session
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        service.data["serviceArn"] = "arn:aws:ecs:1:service/foobar-cluster/foobar-test"
        with patch.object(
            service, "render_for_scale", return_value={"cluster": "foobar-cluster"}
        ):
            Service.objects.scale(service, 3)
        client.update_service.assert_called_once()
