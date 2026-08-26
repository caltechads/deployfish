from deployfish.main import DeployfishApp


class TestPostgresPluginLoading:
    def test_postgres_plugin_is_loaded(self) -> None:
        app = DeployfishApp()
        app.setup()
        assert "postgres" in app.plugin.get_loaded_plugins()

    def test_postgres_controller_has_all_eight_verbs(self) -> None:
        app = DeployfishApp()
        app.setup()
        controller_cls = app.handler.get("controller", "postgres", setup=False)
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
