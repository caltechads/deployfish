from unittest.mock import MagicMock, patch

import pytest
from deployfish.controllers.tunnel import (
    establish_tunnel,
    get_tunnel,
    get_tunnel_target,
)
from deployfish.core.models.ec2 import Instance


class TestGetTunnelTarget:
    def test_get_tunnel_target_default_first_instance(self) -> None:
        obj = MagicMock()
        target = MagicMock(spec=Instance)
        obj.tunnel_target = target
        assert get_tunnel_target(obj, choose=False) is target

    def test_get_tunnel_target_prompts_when_choose(self) -> None:
        obj = MagicMock()
        target = MagicMock(spec=Instance)
        target.name = "instance-1"
        target.pk = "i-123"
        target.ip_address = "10.0.0.1"
        obj.tunnel_targets = [target]
        prompt = MagicMock()
        prompt.prompt.return_value = 1
        with patch("deployfish.controllers.tunnel.shell.Prompt", return_value=prompt):
            with patch("deployfish.controllers.tunnel.click.secho"):
                with patch("deployfish.controllers.tunnel.tabulate", return_value="table"):
                    result = get_tunnel_target(obj, choose=True)
        assert result is target

    def test_get_tunnel_target_raises_when_none(self) -> None:
        obj = MagicMock()
        obj.tunnel_target = None
        obj.__class__.__name__ = "Service"
        obj.pk = "cluster:service"
        with pytest.raises(Instance.DoesNotExist):
            get_tunnel_target(obj, choose=False)


class TestGetTunnel:
    def test_get_tunnel_lists_available(self) -> None:
        tunnel = MagicMock()
        tunnel.name = "mysql-qa"
        tunnel.host = "db.example.com"
        tunnel.host_port = 3306
        tunnel.local_port = 13306
        with patch(
            "deployfish.controllers.tunnel.SSHTunnel.objects.list",
            return_value=[tunnel],
        ):
            with patch("deployfish.controllers.tunnel.click.prompt", return_value=1):
                with patch("deployfish.controllers.tunnel.click.secho"):
                    with patch("deployfish.controllers.tunnel.tabulate", return_value="table"):
                        result = get_tunnel()
        assert result is tunnel


class TestEstablishTunnel:
    def test_establish_tunnel_delegates_to_ssh_provider(self) -> None:
        tunnel = MagicMock()
        tunnel.host = "db.example.com"
        tunnel.host_port = 3306
        tunnel.local_port = 13306
        obj = MagicMock()
        target = MagicMock(spec=Instance)
        target.name = "instance-1"
        target.ip_address = "10.0.0.1"
        obj.tunnel_target = target
        obj.ssh_proxy_type = "ssm"
        with patch("deployfish.controllers.tunnel.click.secho"):
            establish_tunnel(tunnel, obj, choose=False, verbose=False)
        obj.tunnel.assert_called_once_with(tunnel, verbose=False, tunnel_target=target)

    def test_establish_tunnel_raises_when_no_target(self) -> None:
        tunnel = MagicMock()
        obj = MagicMock()
        obj.tunnel_target = None
        with pytest.raises(Instance.DoesNotExist, match="Couldn't find an instance"):
            establish_tunnel(tunnel, obj)
