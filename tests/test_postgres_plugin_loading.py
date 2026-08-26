from pathlib import Path

import pytest
from deployfish.main import DeployfishApp


@pytest.fixture
def postgres_enabled_app(tmp_path: Path) -> DeployfishApp:
    """
    Build a :py:class:`deployfish.main.DeployfishApp` that is fully isolated
    from any config files/dirs on the machine running the test (e.g. a
    developer's ``~/.deployfish.yml``), and that has only the ``postgres``
    plugin enabled via a throwaway config file.

    Args:
        tmp_path: pytest's per-test temporary directory.

    Returns:
        A ``DeployfishApp`` instance that has already had ``setup()`` called.

    """
    config_file = tmp_path / "deployfish-test-config.yml"
    config_file.write_text("plugin.postgres:\n  enabled: true\n")

    app = DeployfishApp(
        config_files=[str(config_file)],
        core_user_config_files=[],
        core_system_config_files=[],
        core_user_config_dirs=[],
        core_system_config_dirs=[],
        config_dirs=[],
    )
    app.setup()
    return app


class TestPostgresPluginLoading:
    def test_postgres_plugin_is_loaded(
        self, postgres_enabled_app: DeployfishApp
    ) -> None:
        assert "postgres" in postgres_enabled_app.plugin.get_loaded_plugins()

    def test_postgres_controller_has_all_eight_verbs(
        self, postgres_enabled_app: DeployfishApp
    ) -> None:
        controller_cls = postgres_enabled_app.handler.get(
            "controller", "postgres", setup=False
        )
        exposed = {
            member
            for member in dir(controller_cls)
            if hasattr(getattr(controller_cls, member), "__cement_meta__")
        }
        expected = {
            "info",
            "create",
            "update",
            "validate",
            "dump",
            "load",
            "show_grants",
            "server_version",
        }
        assert expected <= exposed
