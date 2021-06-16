from deployfish.exceptions import SchemaException


class Adapter(object):

    NONE = 'deployfish:required'

    class SchemaException(SchemaException):
        pass

    def __init__(self, data, **kwargs):
        self.data = data

    def only_one_is_True(self, data):
        """
        Look through the list ``data``, a list of boolean values, and return True if only one True is in the
        list, False otherwise.
        """
        true_found = False
        for v in data:
            if v and not true_found:
                true_found = True
            elif v and true_found:
                return False  # "Too Many Trues"
        return true_found

    def set(self, data, source_key, dest_key=None, default=NONE, optional=False, convert=None):
        if dest_key is None:
            dest_key = source_key
        if self.partial or optional:
            if source_key in self.data:
                data[dest_key] = self.data[source_key]
        else:
            if default != self.NONE:
                data[dest_key] = self.data.get(source_key, default)
            else:
                data[dest_key] = self.data[source_key]
        if dest_key in data and convert:
            data[dest_key] = convert(data[dest_key])

    def convert(self):
        raise NotImplementedError
