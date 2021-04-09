from copy import copy

from .mixins import DeployfishYamlAdapter


class SSHTunnelAdapter(DeployfishYamlAdapter):

    def convert(self):
        data = copy(self.data)
        kwargs = {}
        return data, kwargs
