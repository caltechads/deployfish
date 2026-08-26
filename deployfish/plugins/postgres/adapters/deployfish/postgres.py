from copy import deepcopy

from deployfish.core.adapters.abstract import Adapter


class PostgresDatabaseAdapter(Adapter):
    """
    Model postgres database adapter behavior.
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
