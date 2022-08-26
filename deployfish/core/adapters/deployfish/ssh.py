from copy import deepcopy
from typing import Dict, Any, Tuple

from ..abstract import Adapter


class SSHTunnelAdapter(Adapter):

    def convert(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        data = deepcopy(self.data)
        kwargs: Dict[str, Any] = {}
        return data, kwargs
