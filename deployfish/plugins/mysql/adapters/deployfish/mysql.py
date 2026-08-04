from copy import deepcopy

from deployfish.core.adapters.abstract import Adapter


class MySQLDatabaseAdapter(Adapter):
    """
    Model my sqldatabase adapter behavior.
    """
    def convert(self):
        """
        Convert.

        Returns:
            Operation result.
        """
        data = deepcopy(self.data)
        kwargs = {}
        return data, kwargs
