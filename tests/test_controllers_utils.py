from unittest.mock import MagicMock

from deployfish.controllers.utils import handle_model_exceptions
from deployfish.core.loaders import ObjectLoader
from deployfish.core.models.ecs import Cluster, Service
from deployfish.exceptions import NoSuchConfigSectionItem


class _StubController:
    def __init__(self, app: MagicMock) -> None:
        self.app = app
        self.model = Service
        self.loader = ObjectLoader


class TestHandleModelExceptions:
    def test_catches_does_not_exist(self, cement_app: MagicMock) -> None:
        controller = _StubController(cement_app)

        @handle_model_exceptions
        def failing(_self) -> None:
            msg = "missing service"
            raise Service.DoesNotExist(msg)

        failing(controller)
        cement_app.print.assert_called_once()
        assert "missing service" in cement_app.print.call_args[0][0]

    def test_catches_no_such_config_section_item(self, cement_app: MagicMock) -> None:
        controller = _StubController(cement_app)
        cement_app.deployfish_config.get_section.return_value = [
            {"name": "svc-a", "environment": "prod"},
        ]

        @handle_model_exceptions
        def failing(_self) -> None:
            msg = "services"
            raise NoSuchConfigSectionItem(msg, "missing")

        failing(controller)
        printed = cement_app.print.call_args[0][0]
        assert "missing" in printed

    def test_returns_value_on_success(self, cement_app: MagicMock) -> None:
        controller = _StubController(cement_app)

        @handle_model_exceptions
        def ok(_self) -> str:
            return "done"

        assert ok(controller) == "done"

    def test_readonly_cluster_save_via_decorator(self, cement_app: MagicMock) -> None:
        controller = _StubController(cement_app)
        controller.model = Cluster

        @handle_model_exceptions
        def failing(_self) -> None:
            msg = "read only"
            raise Cluster.ReadOnly(msg)

        failing(controller)
        assert "read only" in cement_app.print.call_args[0][0]
