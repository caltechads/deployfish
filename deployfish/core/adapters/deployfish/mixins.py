from typing import Any


class SSHConfigMixin:

    data: dict[str, Any]

    def convert(self) -> tuple[dict[str, Any], dict[str, Any]]:
        data: dict[str, Any] = {}
        kwargs: dict[str, Any] = {}
        if "ssh" in self.data:
            if "proxy" in self.data["ssh"]:
                kwargs["ssh_proxy_type"] = self.data["ssh"]["proxy"]
        return data, kwargs
