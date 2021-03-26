
class SchemaException(Exception):
    pass


class ObjectDoesNotExist(Exception):
    pass


class MultipleObjectsReturned(Exception):
    pass


class ObjectImproperlyConfigured(Exception):
    pass


class ObjectReadOnly(Exception):
    pass


class OperationalError(Exception):
    pass
