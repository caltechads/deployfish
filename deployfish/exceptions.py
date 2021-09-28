class SchemaException(Exception):
    """
    There was a schema validation problem in the deployfish.yml file.
    """
    pass


class ObjectDoesNotExist(Exception):
    """
    We tried to get a single object but it does not exist in AWS.
    """
    pass


class MultipleObjectsReturned(Exception):
    """
    We expected to retrieve only one object but got multiple objects.
    """
    pass


class ObjectImproperlyConfigured(Exception):
    """
    Deployfish, our model's manager Manager or the model itself is not properly configured.
    """
    pass


class ObjectReadOnly(Exception):
    """
    This is a read only model; no writes to AWS permitted.
    """
    pass


class OperationFailed(Exception):
    """
    We tried to do something we expected to succeed, but it failed.
    """
    pass


class RenderException(Exception):
    """
    This is used for click commands, and gets re-raised when we get other exceptions so we can
    have a consistent method for configuring command line error messages instead of needing
    to catch every exception separately.
    """

    def __init__(self, msg, exit_code=1):
        self.msg = msg
        self.exit_code = exit_code


class NoSuchTerraformStateFile(Exception):
    """
    deployfish.yml references a Terraform state file that doesn't exist.
    """
    pass


class ConfigProcessingFailed(Exception):
    """
    While performing our variable substitutions in deployfish.yml, we had a problem.
    """
    pass


class SkipConfigProcessing(Exception):
    """
    This is used to skip processing steps when looping through the variable substitution classes
    while processing variable substitutions in deployfish.yml.
    """
    pass
