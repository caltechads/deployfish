from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.controllers.service import ECSService

from tests.controller_helpers import bind_controller, bind_service_loader


class TestCrudBaseUpdate:
    def test_update_saves_object(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.name = "foobar-test"
        mock_service = MagicMock()
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_deployfish", return_value=mock_service):
            with patch.object(controller, "update_waiter"):
                with patch(
                    "deployfish.controllers.crud.click.style",
                    side_effect=lambda value, **_: value,
                ):
                    controller.update()
        mock_service.save.assert_called_once()
