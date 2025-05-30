from typing import Any, cast

from deployfish.core.models import Model
from deployfish.exceptions import (
    NoSuchConfigSection,
    NoSuchConfigSectionItem,
    ObjectReadOnly,
)
from deployfish.ext.ext_df_argparse import DeployfishArgparseController


class ServiceDereferenceMixin:
    """
    A mixin for Service objects to support dereferencing of identifiers in the
    form "name" or "environment" into the usual
    "``{cluster_name}:{service_name}``".
    """

    controller: DeployfishArgparseController

    def dereference_identifier(self, identifier: str) -> str:
        """
        For Services, allow users to specify just Service.name or
        Service.environment and dereference that into our usual
        "{cluster_name}:{service_name}" primary key.

        Args:
            identifier: the name of the item to load from the section named by
                `self.model.config_section`

        Returns:
            A ``{cluster_name}:{service_name}`` string

        """
        config = self.controller.app.deployfish_config
        if ":" not in identifier:
            item = config.get_section_item(self.controller.model.config_section, identifier)
            return "{}:{}".format(item["cluster"], item["name"])
        return identifier


class ObjectLoader:
    """
    A base class for loading objects from deployfish.yml or from AWS.
    """

    class DeployfishSectionDoesNotExist(NoSuchConfigSection):
        """
        We raise this when we can't find the section in deployfish.yml that
        the object we're trying to load is supposed to be in.
        """


    class DeployfishObjectDoesNotExist(NoSuchConfigSectionItem):
        """
        We raise this when we can't find the object in the section in
        deployfish.yml that the object we're trying to load is supposed to be
        in.
        """


    class ObjectNotManaged(Exception):
        """
        We raise this if the object we're trying to load is not managed in
        deployfish.yml.
        """


    class ReadOnly(ObjectReadOnly):
        """
        We raise this if this object is read-only.
        """


    def __init__(self, controller):
        self.controller = controller

    def dereference_identifier(self, identifier: str) -> str:
        return identifier

    def get_object_from_aws(
        self,
        identifier: str,
        model: type[Model] | None = None
    ) -> Model:
        """
        Get an object from AWS directly, and don't look at our config in
        deployfish.yml.

        Args:
            identifier: the name of the item to load from the section named by
                ``self.model.config_section``

        Keyword Arguments:
            model: Override the model on self.controller with this class

        Returns:
            A Model instance.

        """
        if not model:
            model = self.controller.model
        model = cast("type[Model]", model)
        if model.config_section != "NO_SECTION":
            identifier = self.dereference_identifier(identifier)
        return model.objects.get(identifier)

    def get_object_from_deployfish(
        self,
        identifier: str,
        factory_kwargs: dict[str, Any] | None = None,
        model: type[Model] | None = None
    ) -> Model:
        """
        Load an object from deployfish.yml.  This may differ from the object in
        AWS.  If you want the object from AWS, use
        :py:meth:`get_object_from_aws`.

        Args:
            identifier: the name of the object in deployfish.yml

        Keyword Arguments:
            factory_kwargs: A dict of additional kwargs to pass to
                ObjectLoader.factory()
            model: Override the model on self.controller with this class

        Raises:
            ObjectLoader.ObjectNotManaged: if this type of object never gets
                defined in deployfish.yml

        Returns:
            A Model instance

        """
        if factory_kwargs is None:
            factory_kwargs = {}
        if not model:
            model = self.controller.model
        model = cast("type[Model]", model)
        if model.config_section != "NO_SECTION":
            return self.factory(identifier, factory_kwargs=factory_kwargs, model=model)
        raise self.ObjectNotManaged(f"{model.__name__} objects are not managed in deployfish.yml")

    def factory(
        self,
        identifier: str,
        factory_kwargs: dict[str, Any] | None = None,
        model: type[Model] | None = None
    ) -> Model:
        """
        Load an object from deployfish.yml.  Look in the section named by
        ``self.model.config_section`` for the entry named `identifier` and
        return a fully configured self.model object.

        Args:
            identifier: the name of the item to load from the section named by
                ``self.model.config_section``

        Keyword Arguments:
            factory_kwargs: kwargs to pass into ``self.model.new()``
            model: Override the model on self.controller with this class

        Returns:
            A Model instance.

        """
        if factory_kwargs is None:
            factory_kwargs = {}
        config = self.controller.app.deployfish_config
        if not model:
            model = self.controller.model
        model = cast("type[Model]", model)
        if not factory_kwargs:
            factory_kwargs = {}
        if model.config_section != "NO_SECTION":
            try:
                config.get_section(model.config_section)
            except KeyError as e:
                raise self.DeployfishSectionDoesNotExist(model.config_section) from e
            try:
                data = config.get_section_item(model.config_section, identifier)
                return model.new(data, "deployfish", **factory_kwargs)
            except KeyError as e:
                raise self.DeployfishObjectDoesNotExist(model.config_section, identifier) from e
        else:
            raise self.ObjectNotManaged(f"deployfish.yml does not manage objects of class {model.__class__}")


class ServiceLoader(ServiceDereferenceMixin, ObjectLoader):
    """
    A loader for Service objects.
    """

