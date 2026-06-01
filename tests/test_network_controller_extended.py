from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.controllers.network import get_ssh_target
from deployfish.core.models.ec2 import Instance
from deployfish.core.models.ecs import Service

from tests.fixtures import SERVICE_YML


class TestGetSSHTargetChoose:
    def test_get_ssh_target_prompts_when_choose(self) -> None:
        app = MagicMock()
        target_a = Instance(
            {
                "InstanceId": "i-a",
                "PrivateIpAddress": "10.0.0.1",
                "PublicDnsName": "",
                "PrivateDnsName": "a.internal",
                "Tags": [{"Key": "Name", "Value": "a"}],
            }
        )
        target_b = Instance(
            {
                "InstanceId": "i-b",
                "PrivateIpAddress": "10.0.0.2",
                "PublicDnsName": "",
                "PrivateDnsName": "b.internal",
                "Tags": [{"Key": "Name", "Value": "b"}],
            }
        )
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        prompt = MagicMock()
        prompt.prompt.return_value = "2"
        with patch.object(
            type(service), "ssh_targets", property(lambda _self: [target_a, target_b])
        ):
            with patch(
                "deployfish.controllers.network.shell.Prompt", return_value=prompt
            ):
                result = get_ssh_target(app, service, choose=True)
        assert result is target_b
