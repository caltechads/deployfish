from copy import deepcopy
from unittest.mock import patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.models.ecs import Cluster, Service

from tests.fixtures import SERVICE_YML


def _service_without_appscaling() -> Service:
    service = Service.new(deepcopy(SERVICE_YML), "deployfish")
    service.appscaling = None
    return service


class TestModelDiffAndEquality:
    def test_diff_detects_changes(self) -> None:
        ours = _service_without_appscaling()
        theirs = _service_without_appscaling()
        with patch.object(ours, "render_for_diff", return_value={"field": "old"}):
            with patch.object(theirs, "render_for_diff", return_value={"field": "new"}):
                diff = ours.diff(theirs)
        assert diff

    def test_diff_raises_for_wrong_type(self) -> None:
        service = _service_without_appscaling()
        cluster = Cluster({"clusterName": "c", "clusterArn": "arn:1"})
        with pytest.raises(ValueError, match="Cluster"):
            service.diff(cluster)

    def test_equality_uses_render_for_diff(self) -> None:
        first = _service_without_appscaling()
        second = _service_without_appscaling()
        assert first == second

    def test_exists_delegates_to_manager(self) -> None:
        service = _service_without_appscaling()
        with patch.object(Service.objects, "exists", return_value=True) as exists_mock:
            assert service.exists is True
        exists_mock.assert_called_once_with(service.pk)

    def test_copy_produces_new_instance(self) -> None:
        service = _service_without_appscaling()
        copied = service.copy()
        assert copied.pk == service.pk
        assert copied is not service

    def test_str_representation(self) -> None:
        service = _service_without_appscaling()
        assert str(service) == f'Service(pk="{service.pk}")'

    def test_reload_from_db_replaces_data(self) -> None:
        service = _service_without_appscaling()
        replacement = _service_without_appscaling()
        replacement.data["desiredCount"] = 9
        with patch.object(Service.objects, "get", return_value=replacement):
            service.reload_from_db()
        assert service.data["desiredCount"] == 9

    def test_manager_diff(self) -> None:
        service = _service_without_appscaling()
        aws_service = _service_without_appscaling()
        with patch.object(service, "render_for_diff", return_value={"field": "old"}):
            with patch.object(
                aws_service, "render_for_diff", return_value={"field": "new"}
            ):
                with patch.object(Service.objects, "get", return_value=aws_service):
                    result = Service.objects.diff(service)
        assert result
