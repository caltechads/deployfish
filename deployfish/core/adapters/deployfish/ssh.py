from copy import deepcopy
from typing import Any

from ..abstract import Adapter


class SSHTunnelAdapter(Adapter):

    def convert(self) -> tuple[dict[str, Any], dict[str, Any]]:
        data = deepcopy(self.data)
        kwargs: dict[str, Any] = {}
        return data, kwargs
