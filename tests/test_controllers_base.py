from unittest.mock import MagicMock, patch

from deployfish.controllers.base import (
    BaseServiceSecrets,
    filename_envvar,
    maybe_rename_existing_file,
)


class TestBaseControllerHelpers:
    def test_filename_envvar_uses_environment(self, monkeypatch) -> None:
        monkeypatch.setenv("DEPLOYFISH_CONFIG_FILE", "/tmp/custom.yml")
        assert filename_envvar("deployfish.yml") == "/tmp/custom.yml"

    def test_filename_envvar_returns_default(self, monkeypatch) -> None:
        monkeypatch.delenv("DEPLOYFISH_CONFIG_FILE", raising=False)
        assert filename_envvar("deployfish.yml") == "deployfish.yml"

    def test_maybe_rename_existing_file(self, tmp_path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("OLD=1\n", encoding="utf-8")
        obj = MagicMock()
        obj.__class__.__name__ = "Service"
        obj.name = "foobar-test"
        with patch("deployfish.controllers.base.click.secho"):
            maybe_rename_existing_file(str(env_file), obj)
        assert not env_file.exists()
        backups = list(tmp_path.glob(".env.*"))
        assert len(backups) == 1


class TestBaseServiceSecretsSync:
    def test_sync_writes_env_files(self, cement_app: MagicMock, tmp_path) -> None:
        from tests.controller_helpers import bind_controller, bind_service_loader

        controller = bind_controller(BaseServiceSecrets(), cement_app)
        env_file = tmp_path / "service.env"
        cement_app.raw_deployfish_config = MagicMock()
        cement_app.raw_deployfish_config.services = [
            {"name": "foobar-test", "env_file": str(env_file)},
        ]
        cement_app.raw_deployfish_config.tasks = []
        cement_app.pargs.ignore_missing_environment = False
        mock_service = MagicMock()
        mock_service.name = "foobar-test"
        mock_service.secrets_prefix = "prefix."
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_deployfish", return_value=mock_service):
            with patch.object(controller, "export_environment_secrets", return_value="A=1\n"):
                with patch("deployfish.controllers.base.click.secho"):
                    controller.sync()
        assert env_file.read_text(encoding="utf-8") == "A=1\n"
