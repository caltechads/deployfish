from copy import deepcopy

from ..abstract import Adapter


class SSHTunnelAdapter(Adapter):

    def convert(self):
        data = deepcopy(self.data)
        kwargs = {}
        return data, kwargs
