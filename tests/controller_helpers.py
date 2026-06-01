from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from deployfish.core.loaders import ObjectLoader, ServiceLoader
from deployfish.ext.ext_df_argparse import DeployfishArgparseController


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


def bind_controller(
    controller: DeployfishArgparseController,
    app: MagicMock,
) -> DeployfishArgparseController:
    controller.app = app
    return controller


def bind_loader_factory(
    controller: DeployfishArgparseController,
    loader: ObjectLoader,
) -> ObjectLoader:
    def loader_factory(_ctrl: DeployfishArgparseController) -> ObjectLoader:
        return loader

    loader_factory_any = cast("Any", loader_factory)

    loader_factory_any.DeployfishSectionDoesNotExist = (
        ObjectLoader.DeployfishSectionDoesNotExist
    )
    loader_factory_any.DeployfishObjectDoesNotExist = (
        ObjectLoader.DeployfishObjectDoesNotExist
    )
    loader_factory_any.ObjectNotManaged = ObjectLoader.ObjectNotManaged
    loader_factory_any.ReadOnly = ObjectLoader.ReadOnly
    controller.loader = loader_factory_any
    return loader


def bind_service_loader(controller: DeployfishArgparseController) -> ServiceLoader:
    loader = ServiceLoader(controller)
    bind_loader_factory(controller, loader)
    return loader
