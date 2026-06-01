from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.controllers.service import ECSServiceSecrets
from deployfish.core.models.ecs import Service
from deployfish.core.models.secrets import Secret

from tests.controller_helpers import bind_controller, bind_service_loader
from tests.fixtures import SERVICE_YML


class TestExportEnvironmentSecrets:
    def test_export_environment_secrets_builds_dotenv(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceSecrets(), cement_app)
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service_yml = deepcopy(SERVICE_YML)
        service_yml["config"] = [
            "DJANGO_SECRET_KEY=${env.DJANGO_SECRET_KEY}",
            "DEBUG=False",
        ]
        cement_app.deployfish_config.get_raw_section_item.return_value = service_yml
        secrets = [
            Secret(
                {
                    "Name": f"{service.secrets_prefix}DJANGO_SECRET_KEY",
                    "Value": "secret-value",
                },
                name="DJANGO_SECRET_KEY",
            ),
        ]
        with patch.object(Secret.objects, "list", return_value=secrets):
            result = controller.export_environment_secrets(service)
        assert result == "DJANGO_SECRET_KEY=secret-value"

    def test_export_skips_external_parameter_specs(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceSecrets(), cement_app)
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service_yml = deepcopy(SERVICE_YML)
        service_yml["config"] = [
            "/path/to/external:external",
            "DJANGO_SECRET_KEY=${env.DJANGO_SECRET_KEY}",
        ]
        cement_app.deployfish_config.get_raw_section_item.return_value = service_yml
        secrets = [
            Secret(
                {
                    "Name": f"{service.secrets_prefix}DJANGO_SECRET_KEY",
                    "Value": "secret-value",
                },
                name="DJANGO_SECRET_KEY",
            ),
        ]
        with patch.object(Secret.objects, "list", return_value=secrets):
            result = controller.export_environment_secrets(service)
        assert "/path/to/external" not in result
        assert result == "DJANGO_SECRET_KEY=secret-value"


class TestSecretsControllerRender:
    def test_show_renders_secrets_template(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceSecrets(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            with patch.object(service, "reload_secrets"):
                controller.show()
        cement_app.render.assert_called_once()
        assert cement_app.render.call_args.kwargs["template"] == controller.show_template

    def test_diff_renders_diff_template(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceSecrets(), cement_app)
        cement_app.pargs.pk = "foobar-test"
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        loader = bind_service_loader(controller)
        changes = {"added": ["DEBUG"]}
        with patch.object(loader, "get_object_from_deployfish", return_value=service):
            with patch.object(service, "diff_secrets", return_value=changes):
                with patch.object(Secret.objects, "list", return_value=[]):
                    with patch(
                        "deployfish.controllers.secrets.click.style",
                        side_effect=lambda value, **_: value,
                    ):
                        controller.diff()
        cement_app.render.assert_called_once()
        assert cement_app.render.call_args.kwargs["template"] == controller.diff_template
