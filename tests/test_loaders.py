from unittest.mock import Mock, patch

import pytest
from deployfish.core.loaders import ObjectLoader, ServiceLoader
from deployfish.core.models.ecs import Service


@pytest.fixture
def mock_controller() -> Mock:
    controller = Mock()
    controller.model = Service
    controller.app = Mock()
    controller.app.deployfish_config = Mock()
    return controller


class TestServiceLoader:
    def test_dereference_identifier_passthrough_qualified_pk(
        self, mock_controller: Mock
    ) -> None:
        loader = ServiceLoader(mock_controller)
        assert (
            loader.dereference_identifier("cluster-a:service-a")
            == "cluster-a:service-a"
        )

    def test_dereference_identifier_from_name(self, mock_controller: Mock) -> None:
        mock_controller.app.deployfish_config.get_section_item.return_value = {
            "cluster": "cluster-a",
            "name": "service-a",
        }
        loader = ServiceLoader(mock_controller)
        assert loader.dereference_identifier("service-a") == "cluster-a:service-a"

    def test_get_object_from_aws_dereferences_identifier(
        self, mock_controller: Mock
    ) -> None:
        mock_controller.app.deployfish_config.get_section_item.return_value = {
            "cluster": "cluster-a",
            "name": "service-a",
        }
        loader = ServiceLoader(mock_controller)
        with patch.object(
            Service.objects, "get", return_value=Mock(spec=Service)
        ) as get_mock:
            loader.get_object_from_aws("service-a")
        get_mock.assert_called_once_with("cluster-a:service-a")


class TestObjectLoaderFactory:
    def test_factory_returns_model_from_config(self, mock_controller: Mock) -> None:
        service_data = {"name": "svc", "cluster": "cluster-a", "count": 1}
        mock_controller.app.deployfish_config.get_section.return_value = True
        mock_controller.app.deployfish_config.get_section_item.return_value = (
            service_data
        )
        loader = ObjectLoader(mock_controller)
        with patch.object(Service, "new", return_value=Mock(spec=Service)) as new_mock:
            loader.factory("svc", model=Service)
        new_mock.assert_called_once_with(service_data, "deployfish")

    def test_factory_raises_when_section_missing(self, mock_controller: Mock) -> None:
        mock_controller.app.deployfish_config.get_section.side_effect = KeyError(
            "services"
        )
        loader = ObjectLoader(mock_controller)
        with pytest.raises(ObjectLoader.DeployfishSectionDoesNotExist):
            loader.factory("svc", model=Service)

    def test_factory_raises_when_object_missing(self, mock_controller: Mock) -> None:
        mock_controller.app.deployfish_config.get_section.return_value = True
        mock_controller.app.deployfish_config.get_section_item.side_effect = KeyError(
            "missing"
        )
        loader = ObjectLoader(mock_controller)
        with pytest.raises(ObjectLoader.DeployfishObjectDoesNotExist):
            loader.factory("missing", model=Service)
