import pprint

from .abstract import AbstractRenderer


# ========================
# Renderers
# ========================


class JSONRenderer(AbstractRenderer):
    """
    This renderer just pretty prints whatever you give it with an indent of 2 spaces.
    """

    def render(self, data):
        return pprint.pformat(data, indent=2)
