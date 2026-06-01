from unittest.mock import MagicMock, patch

from deployfish.ext.ext_df_plugin import (
    DeployfishCementPluginHandler,
    get_deployfish_plugins,
)


class TestDeployfishPluginHandler:
    def test_get_deployfish_plugins_is_iterable(self) -> None:
        with patch(
            "deployfish.ext.ext_df_plugin.pkg_resources.iter_entry_points",
            return_value=[],
        ):
            assert list(get_deployfish_plugins()) == []

    def test_plugin_handler_tracks_enabled_plugins(self) -> None:
        handler = DeployfishCementPluginHandler()
        handler.app = MagicMock()
        handler.app.config.get_sections.return_value = ["plugin.mysql"]
        handler.app.config.keys.return_value = ["enabled"]
        handler.app.config.get.return_value = "true"
        with patch(
            "deployfish.ext.ext_df_plugin.get_deployfish_plugins",
            return_value=[],
        ):
            handler._setup(handler.app)
        assert "mysql" in handler.get_enabled_plugins()

    def test_get_loaded_plugins_starts_empty(self) -> None:
        handler = DeployfishCementPluginHandler()
        assert handler.get_loaded_plugins() == []
