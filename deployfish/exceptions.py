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


class OperationFailed(Exception):
    pass


class RenderException(Exception):

    def __init__(self, msg, exit_code=1):
        self.msg = msg
        self.exit_code = exit_code


class NoSuchTerraformStateFile(Exception):
    pass


class ConfigProcessingFailed(Exception):
    pass
