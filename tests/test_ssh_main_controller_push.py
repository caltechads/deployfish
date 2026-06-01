"""Coverage push for ssh providers, main app config, and service controller."""

import sys
from copy import deepcopy
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from botocore.exceptions import WaiterError
from deployfish.controllers.service import ECSService
from deployfish.core.models.ec2 import Instance
from deployfish.core.models.ecs import Service
from deployfish.core.ssh import (
    AbstractSSHProvider,
    BastionSSHProvider,
    SSMSSHProvider,
    build_sigint_handler,
)

from tests.controller_helpers import bind_controller, bind_service_loader
from tests.fixtures import SERVICE_YML

DEBUGPY = MagicMock()


def _instance(**overrides: object) -> Instance:
    data = {
        "InstanceId": "i-abc123",
        "PrivateIpAddress": "10.0.0.5",
        "PublicDnsName": "",
        "PrivateDnsName": "ip-10-0-0-5.internal",
        "Tags": [{"Key": "Name", "Value": "worker"}],
    }
    data.update(overrides)
    return Instance(data)  # type: ignore[arg-type]


class TestAbstractSSHProvider:
    def test_docker_exec_template(self) -> None:
        provider = SSMSSHProvider(_instance())
        cmd = provider.docker_exec().format("family", "container")
        assert "docker exec" in cmd
        assert "family" in cmd

    def test_push_commands(self) -> None:
        provider = SSMSSHProvider(_instance())
        assert provider.push("script.sh") == "cat > script.sh"
        assert "bash" in provider.push("script.sh", run=True)


class TestBastionSSHProviderExtended:
    def test_tunnel_builds_two_hop_command(self) -> None:
        instance = _instance()
        bastion = _instance(
            InstanceId="i-bastion",
            PublicDnsName="bastion.example.com",
        )  # type: ignore[arg-type]
        with patch.object(Instance, "bastion", new_callable=PropertyMock, return_value=bastion):
            provider = BastionSSHProvider(instance, verbose=True)
            cmd = provider.tunnel(3306, "db.internal", 3306)
        assert "3306" in cmd
        assert bastion.hostname in cmd

    def test_ssh_without_bastion_raises(self) -> None:
        instance = _instance()
        with patch.object(Instance, "bastion", new_callable=PropertyMock, return_value=None):
            provider = BastionSSHProvider.__new__(BastionSSHProvider)
            AbstractSSHProvider.__init__(provider, instance)
            with pytest.raises(ValueError, match="bastion"):
                provider.ssh()

    def test_docker_exec_overrides_template(self) -> None:
        instance = _instance()
        bastion = _instance(InstanceId="i-bastion", PublicDnsName="bastion.example.com")  # type: ignore[arg-type]
        with patch.object(Instance, "bastion", new_callable=PropertyMock, return_value=bastion):
            provider = BastionSSHProvider(instance)
            assert "docker exec" in provider.docker_exec()


class TestSSMSSHProviderPush:
    def test_push_with_run_flag(self) -> None:
        provider = SSMSSHProvider(_instance())
        assert "bash" in provider.push("deploy.sh", run=True)


class TestBuildSigintHandler:
    def test_handler_forwards_signal(self) -> None:
        process = MagicMock()
        handler = build_sigint_handler(process)
        handler(2, None)
        process.send_signal.assert_called_once()


class TestDeployfishAppConfig:
    def test_deployfish_config_lazy_load(self) -> None:
        with patch.dict(sys.modules, {"debugpy": DEBUGPY}):
            from deployfish.main import DeployfishApp

            app = DeployfishApp()
            pargs = MagicMock()
            pargs.deployfish_filename = "deployfish.yml"
            pargs.env_file = None
            pargs.tfe_token = None
            pargs.ignore_missing_environment = False
            mock_config = MagicMock()
            mock_config.get_global_config.return_value = {"ssh": {"proxy": "ssm"}}
            with (
                patch.object(type(app), "pargs", new_callable=PropertyMock, return_value=pargs),
                patch.object(app, "hook") as hook_mock,
                patch.object(app, "config") as config_mock,
                patch("deployfish.main.Config.new", return_value=mock_config),
            ):
                hook_mock.run.return_value = []
                config_mock.get.return_value = "ssm"
                cfg = app.deployfish_config
            assert cfg is mock_config
            assert app._deployfish_config is mock_config

    def test_raw_deployfish_config_lazy_load(self) -> None:
        with patch.dict(sys.modules, {"debugpy": DEBUGPY}):
            from deployfish.main import DeployfishApp

            app = DeployfishApp()
            pargs = MagicMock()
            pargs.deployfish_filename = "deployfish.yml"
            mock_config = MagicMock()
            with (
                patch.object(type(app), "pargs", new_callable=PropertyMock, return_value=pargs),
                patch("deployfish.main.Config.new", return_value=mock_config),
            ):
                cfg = app.raw_deployfish_config
            assert cfg is mock_config

    def test_main_assertion_error_with_debug(self) -> None:
        with patch.dict(sys.modules, {"debugpy": DEBUGPY}):
            from deployfish.main import main

            app = MagicMock()
            app.run.side_effect = AssertionError("bad assert")
            app.debug = True
            with patch("deployfish.main.DeployfishApp") as app_cls:
                app_cls.return_value.__enter__.return_value = app
                app_cls.return_value.__exit__.return_value = False
                with patch("deployfish.main.set_app"):
                    with patch("deployfish.main.maybe_do_cli_debugging"):
                        with patch("traceback.print_exc") as tb_mock:
                            main()
            tb_mock.assert_called_once()
            assert app.exit_code == 1

    def test_maybe_do_cli_debugging_connection_refused(self) -> None:
        with patch.dict(sys.modules, {"debugpy": DEBUGPY}):
            from deployfish.main import maybe_do_cli_debugging

            DEBUGPY.connect.side_effect = ConnectionRefusedError
            argv = ["deploy", "--debugpy"]
            with patch("builtins.print") as print_mock:
                maybe_do_cli_debugging(argv)
            assert "--debugpy" not in argv
            print_mock.assert_called()


class TestECSServiceControllerWaiters:
    def test_service_waiter_passes_cluster_and_service(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        with patch.object(controller, "wait") as wait_mock:
            controller.service_waiter(service)
        wait_mock.assert_called_once()
        kwargs = wait_mock.call_args.kwargs
        assert kwargs["cluster"] == "foobar-cluster"
        assert kwargs["services"] == ["foobar-test"]

    def test_delete_waiter_ignores_draining_error(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        service = MagicMock()
        service.name = "foobar-test"
        service.data = {"cluster": "foobar-cluster"}
        with patch.object(
            controller,
            "wait",
            side_effect=WaiterError("n", "DRAINING", None),
        ):
            controller.delete_waiter(service)

    def test_delete_waiter_reraises_other_waiter_errors(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        service = MagicMock()
        service.name = "foobar-test"
        service.data = {"cluster": "foobar-cluster"}
        with patch.object(
            controller,
            "wait",
            side_effect=WaiterError("n", "reason", {"Error": {"Message": "FAILED"}}),
        ), pytest.raises(WaiterError):
            controller.delete_waiter(service)

    def test_scale_runs_hooks_and_waiter(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.count = 3
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            with patch.object(service, "scale"):
                with patch.object(controller, "scale_services_waiter"):
                    controller.scale()
        cement_app.hook.run.assert_called()
