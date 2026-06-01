import signal
import subprocess
from unittest.mock import MagicMock, PropertyMock, patch

from deployfish.core.models.ec2 import Instance
from deployfish.core.ssh import BastionSSHProvider, SSMSSHProvider, build_sigint_handler


def _instance(
    instance_id: str = "i-abc123",
    ip: str = "10.0.0.5",
    name: str = "test-instance",
) -> Instance:
    return Instance(
        {
            "InstanceId": instance_id,
            "PrivateIpAddress": ip,
            "PublicDnsName": "",
            "PrivateDnsName": f"ip-{ip.replace('.', '-')}.internal",
            "Tags": [{"Key": "Name", "Value": name}],
        }
    )


class TestBuildSigintHandler:
    def test_sigint_handler_forwards_to_subprocess(self) -> None:
        process = MagicMock(spec=subprocess.Popen)
        handler = build_sigint_handler(process)
        handler(signal.SIGINT, None)
        process.send_signal.assert_called_once_with(signal.SIGINT)


class TestSSMSSHProvider:
    def test_ssm_provider_ssh_command_includes_instance_id(self) -> None:
        instance = _instance()
        session = MagicMock()
        session.profile_name = None
        with patch("deployfish.core.ssh.get_boto3_session", return_value=session):
            provider = SSMSSHProvider(instance, verbose=False)
            command = provider.ssh()
        assert "i-abc123" in command
        assert command.startswith("ssh")

    def test_ssm_provider_tunnel_command(self) -> None:
        instance = _instance()
        session = MagicMock()
        session.profile_name = "myprofile"
        with patch("deployfish.core.ssh.get_boto3_session", return_value=session):
            provider = SSMSSHProvider(instance, verbose=True)
            command = provider.tunnel(3306, "db.internal", 3306)
        assert "3306:db.internal:3306" in command
        assert "i-abc123.myprofile" in command


class TestBastionSSHProvider:
    def test_bastion_provider_ssh_command(self) -> None:
        from deployfish.core.models.ec2 import Instance

        instance = _instance(ip="10.0.0.5")
        bastion = _instance(instance_id="i-bastion", ip="54.0.0.1", name="bastion")
        with patch.object(Instance, "bastion", new_callable=PropertyMock, return_value=bastion):
            provider = BastionSSHProvider(instance, verbose=False)
            command = provider.ssh("uptime")
        assert bastion.hostname in command
        assert "10.0.0.5" in command
        assert "uptime" in command
