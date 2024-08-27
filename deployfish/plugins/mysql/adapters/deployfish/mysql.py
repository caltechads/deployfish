from copy import deepcopy

from deployfish.core.adapters.abstract import Adapter


class MySQLDatabaseAdapter(Adapter):

    def convert(self):
        data = deepcopy(self.data)
        kwargs = {}
        return data, kwargs
