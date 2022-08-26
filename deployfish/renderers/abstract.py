from typing import Any


class AbstractRenderer:

    def __init__(self, *args, **kwargs):
        pass

    def render(self, data: Any, **kwargs: Any) -> str:
        raise NotImplementedError
