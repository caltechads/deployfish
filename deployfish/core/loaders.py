from typing import Type, Optional, Dict, Any, cast

from deployfish.core.models import Model
from deployfish.exceptions import NoSuchConfigSection, NoSuchConfigSectionItem, ObjectReadOnly
from deployfish.ext.ext_df_argparse import DeployfishArgparseController


class ServiceDereferenceMixin:

    controller: DeployfishArgparseController

    def dereference_identifier(self, identifier: str) -> str:
        """
        For Services, allow users to specify just Service.name or
        Service.environment and dereference that into our usual
        "{cluster_name}:{service_name}" primary key.

        Args:
            identifier: the name of the item to load from the section named by `self.model.config_section`

        Returns:
            A ``{cluster_name}:{service_name}`` string
        """
        config = self.controller.app.deployfish_config
        if ':' not in identifier:
            item = config.get_section_item(self.controller.model.config_section, identifier)
            return '{}:{}'.format(item['cluster'], item['name'])
        return identifier


class ObjectLoader:

    class DeployfishSectionDoesNotExist(NoSuchConfigSection):
        pass

    class DeployfishObjectDoesNotExist(NoSuchConfigSectionItem):
        pass

    class ObjectNotManaged(Exception):
        pass

    class ReadOnly(ObjectReadOnly):
        pass

    def __init__(self, controller):
        self.controller = controller

    def dereference_identifier(self, identifier: str) -> str:
        return identifier

    def get_object_from_aws(self, identifier: str, model: Optional[Type[Model]] = None) -> Model:
        """
        Get an object from AWS directly, and don't look at our config in deployfish.yml.

        Args:
            identifier: the name of the item to load from the section named by `self.model.config_section`

        Keyword Arguments:
            model: Override the model on self.controller with this class

        Returns:
            A Model instance.
        """
        if not model:
            model = self.controller.model
        model = cast(Type[Model], model)
        if model.config_section != 'NO_SECTION':
            identifier = self.dereference_identifier(identifier)
        return model.objects.get(identifier)

    def get_object_from_deployfish(
        self,
        identifier: str,
        factory_kwargs: Optional[Dict[str, Any]] = None,
        model: Optional[Type[Model]] = None
    ) -> Model:
        """
        Load an object from deployfish.yml.  This may differ from the object in AWS.  If you want
        the object from AWS, use ``self.get_object_from_aws()``.

        Args:
            identifier: the name of the object in deployfish.yml

        Keyword Arguments:
            factory_kwargs: A dict of additional kwargs to pass to ObjectLoader.factory()
            model: Override the model on self.controller with this class

        Raises:
            ObjectLoader.ObjectNotManaged: if this type of object never gets defined in deployfish.yml

        Returns:
            A Model instance
        """
        if factory_kwargs is None:
            factory_kwargs = {}
        if not model:
            model = self.controller.model
        model = cast(Type[Model], model)
        if model.config_section != 'NO_SECTION':
            return self.factory(identifier, factory_kwargs=factory_kwargs, model=model)
        raise self.ObjectNotManaged(f'{model.__name__} objects are not managed in deployfish.yml')

    def factory(
        self,
        identifier: str,
        factory_kwargs: Optional[Dict[str, Any]] = None,
        model: Optional[Type[Model]] = None
    ) -> Model:
        """
        Load an object from deployfish.yml.  Look in the section named by
        ``self.model.config_section`` for the entry named `identifier` and
        return a fully configured self.model object.

        Args:
            identifier: the name of the item to load from the section named by ``self.model.config_section``

        Keyword Arguments:
            factory_kwargs: kwargs to pass into `self.model.new()`
            model: Override the model on self.controller with this class

        Returns:
            A Model instance.
        """
        if factory_kwargs is None:
            factory_kwargs = {}
        config = self.controller.app.deployfish_config
        if not model:
            model = self.controller.model
        model = cast(Type[Model], model)
        if not factory_kwargs:
            factory_kwargs = {}
        if model.config_section != 'NO_SECTION':
            try:
                config.get_section(model.config_section)
            except KeyError:
                raise self.DeployfishSectionDoesNotExist(model.config_section)
            try:
                data = config.get_section_item(model.config_section, identifier)
                return model.new(data, 'deployfish', **factory_kwargs)
            except KeyError:
                raise self.DeployfishObjectDoesNotExist(model.config_section, identifier)
        else:
            raise self.ObjectNotManaged('deployfish.yml does not manage objects of class {}'.format(model.__class__))


class ServiceLoader(ServiceDereferenceMixin, ObjectLoader):
    pass
