from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.controllers.network import get_ssh_target
from deployfish.controllers.service import ECSServiceSSH
from deployfish.core.models.ec2 import Instance

from tests.controller_helpers import bind_controller, bind_service_loader
from tests.fixtures import FARGATE_SERVICE_YML, SERVICE_YML


class TestGetSSHTarget:
    def test_get_ssh_target_default(self) -> None:
        app = MagicMock()
        obj = MagicMock()
        target = MagicMock(spec=Instance)
        obj.ssh_target = target
        obj.ssh_targets = [target]
        assert get_ssh_target(app, obj, choose=False) is target

    def test_get_ssh_target_raises_when_none(self) -> None:
        app = MagicMock()
        obj = MagicMock()
        obj.ssh_targets = []
        obj.ssh_target = None
        obj.__class__.__name__ = "Service"
        obj.pk = "cluster:service"
        with pytest.raises(Instance.DoesNotExist):
            get_ssh_target(app, obj, choose=False)


class TestFargateVPCConfiguration:
    def test_fargate_service_yaml_includes_vpc_configuration(self) -> None:
        assert FARGATE_SERVICE_YML["vpc_configuration"]["subnets"] == ["subnet-abc123"]
        assert FARGATE_SERVICE_YML["vpc_configuration"]["security_groups"] == ["sg-abc123"]

    def test_host_service_has_no_vpc_configuration(self) -> None:
        assert "vpc_configuration" not in SERVICE_YML


class TestECSServiceSSHController:
    def test_ssh_calls_target_interactive(self, cement_app: MagicMock) -> None:
        from deployfish.core.models.ec2 import Instance as EC2Instance

        controller = bind_controller(ECSServiceSSH(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.verbose = False
        cement_app.pargs.choose = False
        service = MagicMock()
        service.pk = "foobar-cluster:foobar-test"
        loader = bind_service_loader(controller)
        target = EC2Instance(
            {
                "InstanceId": "i-test",
                "PrivateIpAddress": "10.0.0.1",
                "PublicDnsName": "",
                "PrivateDnsName": "ip-10-0-0-1.internal",
                "Tags": [{"Key": "Name", "Value": "target"}],
            }
        )
        with patch.object(loader, "get_object_from_aws", return_value=service):
            with patch(
                "deployfish.controllers.network.get_ssh_target",
                return_value=target,
            ):
                with patch.object(target, "ssh_interactive") as ssh_mock:
                    controller.ssh()
        ssh_mock.assert_called_once_with(verbose=False)
