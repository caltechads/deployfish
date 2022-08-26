from typing import Dict, Any, Tuple


class SSHConfigMixin:

    data: Dict[str, Any]

    def convert(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        data: Dict[str, Any] = {}
        kwargs: Dict[str, Any] = {}
        if 'ssh' in self.data:
            if 'proxy' in self.data['ssh']:
                kwargs['ssh_proxy_type'] = self.data['ssh']['proxy']
        return data, kwargs
