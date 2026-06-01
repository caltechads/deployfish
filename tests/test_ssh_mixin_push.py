"""SSHMixin and Service networking coverage."""

import tempfile
from copy import deepcopy
from pathlib import PurePosixPath
from typing import Any, Literal
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.models.ec2 import Instance
from deployfish.core.models.ecs import InvokedTask, Service
from deployfish.core.ssh import DockerMixin, SSHMixin, SSMSSHProvider

from tests.fixtures import FARGATE_SERVICE_YML, SERVICE_YML


def _instance() -> Instance:
    return Instance(
        {
            "InstanceId": "i-abc123",
            "PrivateIpAddress": "10.0.0.5",
            "PublicDnsName": "",
            "PrivateDnsName": "ip-10-0-0-5.internal",
            "Tags": [{"Key": "Name", "Value": "worker"}],
        }
    )


class TestServiceSSHNetworking:
    def test_ssh_proxy_type_fargate_forces_ssm(self) -> None:
        service = Service.new(deepcopy(FARGATE_SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        with (
            patch.object(service.task_definition, "is_fargate", return_value=True),
            patch("deployfish.core.ssh.get_config") as config_mock,
        ):
            config_mock.return_value.ssh_provider_type = "bastion"
            assert service.ssh_proxy_type == "ssm"

    def test_ssh_interactive_raises_for_fargate(self) -> None:
        service = Service.new(deepcopy(FARGATE_SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        with (
            patch.object(service.task_definition, "is_fargate", return_value=True),
            pytest.raises(Service.OperationFailed, match="FARGATE"),
        ):
            service.ssh_interactive()

    def test_ssh_noninteractive_raises_for_fargate(self) -> None:
        service = Service.new(deepcopy(FARGATE_SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        with (
            patch.object(service.task_definition, "is_fargate", return_value=True),
            pytest.raises(Service.OperationFailed, match="FARGATE"),
        ):
            service.ssh_noninteractive("uptime")

    def test_ssh_tunnels_loads_from_config(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        service.data["serviceArn"] = "arn:aws:ecs:1:service/foobar-cluster/foobar-test"
        tunnel = MagicMock()
        tunnel.name = "db"
        with patch(
            "deployfish.core.models.ssh.SSHTunnel.objects.list",
            return_value=[tunnel],
        ):
            tunnels = service.ssh_tunnels
        assert tunnels["db"].service is service


class TestSSHMixinHelpers:
    def test_ssh_noninteractive_wraps_command(self) -> None:
        host = MagicMock(spec=SSHMixin)
        host.ssh_proxy_type = "ssm"
        host.ssh_target = _instance()
        instance = _instance()
        with (
            patch("deployfish.core.ssh.get_config") as config_mock,
            patch("deployfish.core.ssh.subprocess.Popen") as popen_mock,
            patch("deployfish.core.ssh.get_boto3_session") as session_mock,
        ):
            config_mock.return_value.ssh_provider_type = "ssm"
            session_mock.return_value.profile_name = None
            process = MagicMock()
            process.communicate.return_value = ("ok\n", "")
            process.returncode = 0
            popen_mock.return_value = process
            success, output = SSHMixin.ssh_noninteractive(
                host,
                "echo hi",
                ssh_target=instance,
            )
        assert success is True
        assert "ok" in output

    def test_ssh_interactive_calls_subprocess(self) -> None:
        host = MagicMock()
        host.ssh_proxy_type = "ssm"
        host.ssh_target = _instance()
        host.providers = SSHMixin.providers
        with (
            patch("deployfish.core.ssh.get_boto3_session") as session_mock,
            patch("deployfish.core.ssh.subprocess.call") as call_mock,
        ):
            session_mock.return_value.profile_name = None
            SSHMixin.ssh_interactive(host)
        call_mock.assert_called_once()

    def test_ssh_interactive_raises_without_target(self) -> None:
        class _Host(SSHMixin):
            cache: dict[str, object] = {}
            data: dict[str, object] = {}
            config_section = "test"
            objects = MagicMock()

            @property
            def pk(self) -> str:
                return "host"

            @property
            def name(self) -> str:
                return "host"

            @property
            def arn(self) -> str | None:
                return None

            def get_cached(
                self,
                _key: str,
                _populator: Any,
                _args: list[Any],
                _kwargs: dict[str, Any] | None = None,
            ) -> None:
                return None

            ssh_target: Instance | None = None

        with pytest.raises(SSHMixin.NoSSHTargetAvailable):
            _Host().ssh_interactive()

    def test_tunnel_calls_subprocess(self) -> None:
        host = MagicMock()
        host.ssh_proxy_type = "ssm"
        host.tunnel_target = _instance()
        host.providers = SSHMixin.providers
        tunnel = MagicMock()
        tunnel.local_port = 3306
        tunnel.host = "db.internal"
        tunnel.host_port = 3306
        with (
            patch("deployfish.core.ssh.get_boto3_session") as session_mock,
            patch("deployfish.core.ssh.subprocess.call") as call_mock,
        ):
            session_mock.return_value.profile_name = None
            SSHMixin.tunnel(host, tunnel)
        call_mock.assert_called_once()

    def test_push_file_uploads_via_ssh(self) -> None:
        host = MagicMock()
        host.ssh_proxy_type = "ssm"
        host.ssh_target = _instance()
        host.providers = SSHMixin.providers
        host.ssh_noninteractive.return_value = (True, "ok")
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write("payload")
            tmp.flush()
            success, _output, remote = SSHMixin.push_file(host, tmp.name)
        assert success is True
        assert PurePosixPath(remote).parts[:2] == ("/", "tmp")


class _DockerHost(DockerMixin):
    config_section = "services"
    objects = MagicMock()

    def __init__(self) -> None:
        self.cache: dict[str, object] = {}
        self.data: dict[str, object] = {}
        self._running_tasks: list[InvokedTask] = []
        self._secrets: dict[str, Any] = {}

    @property
    def running_tasks(self) -> list[InvokedTask]:
        return self._running_tasks

    @property
    def pk(self) -> str:
        return "svc"

    @property
    def name(self) -> str:
        return "svc"

    @property
    def arn(self) -> str | None:
        return None

    @property
    def cluster(self) -> MagicMock:
        cluster = MagicMock()
        cluster.name = "foobar-cluster"
        return cluster

    @property
    def task_definition(self) -> MagicMock:
        td = MagicMock()
        td.data = {"family": "foobar"}
        return td

    @property
    def exec_enabled(self) -> bool:
        return True

    @property
    def ssh_tunnels(self) -> list[Any]:
        return []

    @property
    def secrets(self) -> dict[str, Any]:
        return self._secrets

    @secrets.setter
    def secrets(self, value: dict[str, Any]) -> None:
        self._secrets = value

    @property
    def ssh_proxy_type(self) -> Literal["bastion", "ssm"]:
        return "ssm"

    @property
    def secrets_prefix(self) -> str:
        return "cluster.service."

    def get_cached(
        self,
        _key: str,
        _populator: Any,
        _args: list[Any],
        _kwargs: dict[str, Any] | None = None,
    ) -> None:
        return None

    def reload_secrets(self) -> None:
        self._secrets = {}

    def write_secrets(self) -> None:
        return None

    def diff_secrets(
        self,
        _other: Any,
        ignore_external: bool = False,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        del ignore_external
        return {}


class TestDockerMixinPush:
    def test_docker_ssh_exec_runs_command(self) -> None:
        host = _DockerHost()
        task = MagicMock(spec=InvokedTask)
        task.ssh_target = _instance()
        container = MagicMock()
        container.name = "app_container"
        task.containers = [container]
        host._running_tasks = [task]
        with (
            patch("deployfish.core.ssh.get_boto3_session") as session_mock,
            patch("deployfish.core.ssh.subprocess.call") as call_mock,
            patch("deployfish.core.ssh.click.echo"),
        ):
            session_mock.return_value.profile_name = None
            host.docker_ssh_exec()
        call_mock.assert_called_once()

    def test_docker_ecs_exec_with_profile(self) -> None:
        host = _DockerHost()
        task = MagicMock(spec=InvokedTask)
        task.arn = "arn:aws:ecs:us-west-2:123:task/abc"
        container = MagicMock()
        container.name = "app"
        task.containers = [container]
        host._running_tasks = [task]
        process = MagicMock()
        with (
            patch("deployfish.core.ssh.get_boto3_session") as session_mock,
            patch(
                "deployfish.core.ssh.subprocess.Popen", return_value=process
            ) as popen_mock,
            patch("deployfish.core.ssh.signal.signal"),
            patch(
                "deployfish.core.ssh.build_sigint_handler", return_value=lambda *_: None
            ),
        ):
            session_mock.return_value.profile_name = "dev"
            host.docker_ecs_exec()
        cmd = popen_mock.call_args[0][0]
        assert "--profile dev" in cmd[2]
        process.wait.assert_called_once()

    def test_docker_exec_raises_without_running_tasks(self) -> None:
        host = _DockerHost()
        with pytest.raises(DockerMixin.NoRunningTasks):
            host.docker_ssh_exec()


class TestSSMSSHProviderExtended:
    def test_ssh_includes_profile_suffix(self) -> None:
        instance = _instance()
        with patch("deployfish.core.ssh.get_boto3_session") as session_mock:
            session_mock.return_value.profile_name = "dev"
            cmd = SSMSSHProvider(instance, verbose=True).ssh("uptime")
        assert ".dev" in cmd
        assert "-vv" in cmd
