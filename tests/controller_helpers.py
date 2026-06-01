from unittest.mock import MagicMock

import pytest
from deployfish.core.loaders import ObjectLoader, ServiceLoader


@pytest.fixture
def cement_app() -> MagicMock:
    app = MagicMock()
    app.pargs = MagicMock()
    app.deployfish_config = MagicMock()
    app.render = MagicMock()
    app.print = MagicMock()
    app.log = MagicMock()
    app.debug = False
    app.hook = MagicMock()
    app.hook.run.return_value = []
    return app


def bind_controller(controller: object, app: MagicMock) -> object:
    controller.app = app
    return controller


def bind_loader_factory(controller: object, loader: ObjectLoader) -> ObjectLoader:
    loader_cls = loader.__class__

    def loader_factory(_ctrl: object) -> ObjectLoader:
        return loader

    loader_factory.DeployfishSectionDoesNotExist = (
        ObjectLoader.DeployfishSectionDoesNotExist
    )
    loader_factory.DeployfishObjectDoesNotExist = (
        ObjectLoader.DeployfishObjectDoesNotExist
    )
    loader_factory.ObjectNotManaged = ObjectLoader.ObjectNotManaged
    loader_factory.ReadOnly = ObjectLoader.ReadOnly
    controller.loader = loader_factory  # type: ignore[attr-defined]
    return loader


def bind_service_loader(controller: object) -> ServiceLoader:
    return bind_loader_factory(controller, ServiceLoader(controller))
