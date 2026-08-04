class SchemaException(Exception):
    """
    There was a schema validation problem in the deployfish.yml file.
    """


class ObjectDoesNotExist(Exception):
    """
    We tried to get a single object but it does not exist in AWS.
    """


class MultipleObjectsReturned(Exception):
    """
    We expected to retrieve only one object but got multiple objects.
    """


class ObjectImproperlyConfigured(Exception):
    """
    Deployfish, our model's manager Manager or the model itself is not properly
    configured.
    """


class ObjectReadOnly(Exception):
    """

    is a read only model; no writes to AWS permitted.
    """


class OperationFailed(Exception):
    """
    We tried to do something we expected to succeed, but it failed.
    """


class NoSuchConfigSection(Exception):
    """
    We looked in our deployfish.yml for a section, but it was not present.

    Args:
        section: section.

    """

    def __init__(self, section: str):
        """
        Initialize NoSuchConfigSection.

        Args:
            section: section.

        """
        super().__init__()
        #: Section.
        self.section = section

    def __str__(self) -> str:
        """
        Handle str.

        Returns:
            Operation result.

        """
        return f"No such deployfish.yml section: {self.section}"


class NoSuchConfigSectionItem(Exception):
    """
    We looked an existing deployfish.yml section for a named item, but it was not
    present.

    Args:
        section: section.
        name: name.

    """

    def __init__(self, section: str, name: str):
        """
        Initialize NoSuchConfigSectionItem.

        Args:
            section: section.
            name: name.

        """
        super().__init__()
        #: Section.
        self.section = section
        #: Name.
        self.name = name

    def __str__(self) -> str:
        """
        Handle str.

        Returns:
            Operation result.

        """
        return f'No item named "{self.name}" deployfish.yml section "{self.section}"'


class RenderException(Exception):
    """

    is used for click commands, and gets re-raised when we get other exceptions so
    we can

    Args:
        msg: msg.
        exit_code: exit code.

    """

    def __init__(self, msg: str, exit_code: int = 1):
        #: Msg.
        """
        Initialize RenderException.

        Args:
            msg: msg.
            exit_code: exit code.

        """
        #: Msg.
        self.msg = msg
        #: Exit code.
        self.exit_code = exit_code


class DeployfishAppError(Exception):
    """
    Model deployfish app error behavior.
    """


class NoSuchTerraformStateFile(Exception):
    """
    deployfish.yml references a Terraform state file that doesn't exist.
    """


class ConfigProcessingFailed(Exception):
    """
    While performing our variable substitutions in deployfish.yml, we had a problem.
    """


class SkipConfigProcessing(Exception):
    """

    is used to skip processing steps when looping through the variable substitution
    classes
    while processing variable substitutions in deployfish.yml.
    """
