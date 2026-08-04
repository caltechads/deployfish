"""
Cement plugin extension module.
"""

import re
import sys
from collections.abc import Generator

import pkg_resources
from cement import App
from cement.core import exc, plugin
from cement.utils.misc import is_true, minimal_logger

#: Log.
LOG = minimal_logger(__name__)


def get_deployfish_plugins() -> Generator[pkg_resources.EntryPoint, None, None]:
    """
    We register deployfish plugins via setuptools entrypoints.  To register
    package as a deployfish plugin, in your ``setup.py``,  define
    ``entry_points`` in your ``setup()`` invocation in ``setup.py`` like so::

        # sample ./setup.py file
        from setuptools import setup

        setup(
            name="myproject",
            packages=["myproject"],
            # the following makes a plugin available to pytest
            entry_points={"deployfish.plugins": ["name_of_plugin =
            myproject.pluginmodule"]},
            classifiers=["Framework :: Deployfish"],
        )

    Returns:
        Operation result.

    """
    return pkg_resources.iter_entry_points(group="deployfish.plugins")


class DeployfishCementPluginHandler(plugin.PluginHandler):
    """

    class is an internal implementation of the
    :ref:`IPlugin <cement.core.plugin>` interface. It does not take any
    parameters on initialization.

    """

    class Meta:
        """Handler meta-data."""

        label = "df_plugin"
        """The string identifier for this class."""

    def __init__(self):
        """
        Initialize DeployfishCementPluginHandler.
        """
        super().__init__()
        #: Loaded plugins.
        self._loaded_plugins = []
        #: Enabled plugins.
        self._enabled_plugins = []
        #: Disabled plugins.
        self._disabled_plugins = []

    def _setup(self, app: App) -> None:
        """
        Handle setup.

        Args:
            app: app.

        """
        super()._setup(app)
        self._enabled_plugins = []
        self._disabled_plugins = []
        self.entrypoints = {p.name: p for p in get_deployfish_plugins()}
        LOG.debug("known plugins: {}".format(", ".join(self.entrypoints.keys())))  # noqa: G001

        # parse all app configs for plugins. Note: these are already loaded from
        # files when app.config was setup.  The application configuration
        # OVERRIDES plugin configs.
        for section in self.app.config.get_sections():
            if not section.startswith("plugin."):
                continue
            plugin_section = section
            _plugin = re.sub("^plugin.", "", section)

            if "enabled" not in self.app.config.keys(plugin_section):
                continue
            if is_true(self.app.config.get(plugin_section, "enabled")):
                LOG.debug(f"enabling plugin '{_plugin}' per application config")  # noqa: G004
                if _plugin not in self._enabled_plugins:
                    self._enabled_plugins.append(_plugin)
                if _plugin in self._disabled_plugins:
                    self._disabled_plugins.remove(_plugin)
            else:
                LOG.debug(f"disabling plugin '{_plugin}' per application config")  # noqa: G004
                if _plugin not in self._disabled_plugins:
                    self._disabled_plugins.append(_plugin)
                if _plugin in self._enabled_plugins:
                    self._enabled_plugins.remove(_plugin)

    def load_plugin(self, plugin_name: str) -> None:  # pylint: disable=arguments-differ
        """
        Load plugin.

        Args:
            plugin_name: plugin name.

        """
        LOG.debug(f"loading application plugin '{plugin_name}'")  # noqa: G004
        if (
            plugin_name in self.entrypoints
            and plugin_name not in self.get_loaded_plugins()
        ):
            self._loaded_plugins.append(plugin_name)
            self.entrypoints[plugin_name].load()
            module_name = self.entrypoints[plugin_name].module_name
            if hasattr(sys.modules[module_name], "load"):
                sys.modules[module_name].load(self.app)
            self._loaded_plugins.append(plugin_name)
        else:
            LOG.debug(
                f"no plugin named '{plugin_name}' exists among the known 'deployfish.plugins' entrypoints"  # noqa: E501, G004
            )

    def load_plugins(self, _: list[str]) -> None:
        """
        Load a list of plugins.

        Args:
            plugins: A list of plugin names to load.

        """
        for plugin_name in self.entrypoints:
            if plugin_name in self.get_enabled_plugins():
                self.load_plugin(plugin_name)
                if plugin_name not in self._loaded_plugins:
                    msg = f"Unable to load plugin '{plugin_name}'."
                    raise exc.FrameworkError(msg)
            else:
                LOG.debug(
                    f"found entrypoint for plugin {{{plugin_name}}} but it is disabled in the config"  # noqa: E501, G004
                )

    def get_loaded_plugins(self) -> list[str]:
        """
        List of plugins that have been loaded.

        Returns:
            Operation result.

        """
        return self._loaded_plugins

    def get_enabled_plugins(self) -> list[str]:
        """
        List of plugins that are enabled (not necessary loaded yet).

        Returns:
            Operation result.

        """
        return self._enabled_plugins

    def get_disabled_plugins(self) -> list[str]:
        """
        List of disabled plugins

        Returns:
            Operation result.

        """
        return self._disabled_plugins


def load(app):
    """
    Load.

    Args:
        app: app.

    """
    app.handler.register(DeployfishCementPluginHandler)
