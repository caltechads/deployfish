from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.loaders import ObjectLoader, ServiceLoader
from deployfish.core.models.ecs import Service, StandaloneTask

from tests.fixtures import STANDALONE_TASK_YML


class TestObjectLoaderExtended:
    def test_get_object_from_deployfish(self) -> None:
        controller = MagicMock()
        controller.model = StandaloneTask
        controller.app = MagicMock()
        task_yml = dict(STANDALONE_TASK_YML)
        controller.app.deployfish_config.get_section.return_value = True
        controller.app.deployfish_config.get_section_item.return_value = task_yml
        loader = ObjectLoader(controller)
        with patch.object(StandaloneTask, "new", return_value=MagicMock()) as new_mock:
            loader.get_object_from_deployfish("foobar-test-mytask")
        new_mock.assert_called_once()

    def test_get_object_from_aws(self) -> None:
        controller = MagicMock()
        controller.model = Service
        controller.app = MagicMock()
        loader = ServiceLoader(controller)
        with patch.object(loader, "dereference_identifier", return_value="c:s"):
            with patch.object(Service.objects, "get", return_value=MagicMock()) as get_mock:
                loader.get_object_from_aws("c:s")
        get_mock.assert_called_once_with("c:s")
