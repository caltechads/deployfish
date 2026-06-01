from unittest.mock import MagicMock, patch

from deployfish.controllers.network import ObjectDockerExecController
from deployfish.core.models.ec2 import Instance


class TestObjectDockerExecController:
    def test_get_ssh_exec_target_returns_none_when_not_choosing(self) -> None:
        controller = ObjectDockerExecController()
        obj = MagicMock()
        instance, container = controller.get_ssh_exec_target(obj, choose=False)
        assert instance is None
        assert container is None

    def test_get_ssh_exec_target_prompts_when_choosing(self) -> None:
        controller = ObjectDockerExecController()
        controller.app = MagicMock()
        target = Instance(
            {
                "InstanceId": "i-1",
                "PrivateIpAddress": "10.0.0.1",
                "PublicDnsName": "",
                "PrivateDnsName": "a.internal",
                "Tags": [{"Key": "Name", "Value": "worker"}],
            }
        )
        container = MagicMock()
        container.name = "app"
        container.version = "1"
        task = MagicMock()
        task.ssh_target = target
        task.containers = [container]
        obj = MagicMock()
        obj.running_tasks = [task]
        prompt = MagicMock()
        prompt.prompt.return_value = "1"
        with patch("deployfish.controllers.network.shell.Prompt", return_value=prompt):
            with patch("deployfish.controllers.network.tabulate"):
                with patch("deployfish.controllers.network.click.secho"):
                    instance, container_name = controller.get_ssh_exec_target(obj, choose=True)
        assert instance is target
        assert container_name == "app"
