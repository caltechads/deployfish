from copy import deepcopy
import os
import sys
from typing import Dict, Any, List, Final

import boto3
import click
import yaml

from deployfish.exceptions import ConfigProcessingFailed, NoSuchConfigSection, NoSuchConfigSectionItem
from .processors import ConfigProcessor


class Config:
    """
    This class reads our ``deployfish.yml`` file and handles the allowed
    variable substitutions in string values for service entries under the
    the sections named in :py:attr:`processable_sections`.

    Allowed variable substitutions:

    * ``${terraform.<lookup key>}``:  If we have a ``terraform:`` section
      in our YAML, replace this with the terraform lookup value for
      ``<lookup key>``.

    * ``${env.<environment var>}```:  If the environment variable
      ``<environment var>`` exists in our environment, replace this with
      the value of that environment variable.

    Args:
        filename: the path to our config file

    Keyword Args:
        raw_config: if, supplied, use this as our config data instead of loading
            if from ``filename``
    """

    class NoSuchSectionError(NoSuchConfigSection):
        pass

    class NoSuchSectionItemError(NoSuchConfigSectionItem):
        pass

    #: The default name of our config file
    DEFAULT_DEPLOYFISH_CONFIG_FILE: Final[str] = 'deployfish.yml'

    #: The list of sections in our config file that will be processed
    #: by our :py:class:`deployfish.config.processors.ConfigProcessor`
    processable_sections: List[str] = [
        'services',
        'tasks',
        'tunnels'
    ]

    @classmethod
    def new(cls, **kwargs) -> "Config":
        # FIXME: Why are we doing this as a classmethod instead of just
        # doing it all in __init__?
        filename: str = kwargs.pop('filename', cls.DEFAULT_DEPLOYFISH_CONFIG_FILE)
        if filename is None:
            filename = cls.DEFAULT_DEPLOYFISH_CONFIG_FILE
        config = cls(filename=filename, raw_config=kwargs.pop('raw_config', None))
        if kwargs.pop('interpolate', True):
            try:
                processor = ConfigProcessor(config, kwargs)
                processor.process()
            except ConfigProcessingFailed as e:
                click.secho(str(e))
                sys.exit(1)
        return config

    def __init__(
        self,
        filename: str,
        raw_config: Dict[str, Any] = None,
        boto3_session: boto3.session.Session = None
    ) -> None:
        # FIXME: we're accepting boto3_session as a kwarg, but we never do anything with it
        self.filename: str = filename
        self.__raw: Dict[str, Any] = raw_config if raw_config else self.load_config(filename)
        self.__cooked: Dict[str, Any] = deepcopy(self.__raw)

    @property
    def raw(self) -> Dict[str, Any]:
        """
        Return the pre-interpolated version of the raw YAML.

        Returns:
            The pre-interpolated version of the raw YAML.
        """
        return self.__raw

    @property
    def cooked(self) -> Dict[str, Any]:
        """
        Return the post-interpolated version of the raw YAML.

        Returns:
            The post-interpolated version of the raw YAML.
        """
        return self.__cooked

    @property
    def tasks(self) -> List[Dict[str, Any]]:
        try:
            return self.cooked.get('tasks', [])
        except KeyError:
            raise self.NoSuchSectionError('tasks')

    @property
    def services(self) -> List[Dict[str, Any]]:
        try:
            return self.cooked.get('services', [])
        except KeyError:
            raise self.NoSuchSectionError('services')

    def load_config(self, filename: str) -> Dict[str, Any]:
        """
        Read our deployfish.yml file from disk and return it as parsed YAML.

        :param filename: the path to our deployfish.yml file
        :type filename: string

        :rtype: dict
        """
        if not os.path.exists(filename):
            raise ConfigProcessingFailed("Couldn't find deployfish config file '{}'".format(filename))
        if not os.access(filename, os.R_OK):
            raise ConfigProcessingFailed(
                "Deployfish config file '{}' exists but is not readable".format(filename)
            )
        with open(filename, encoding='utf-8') as f:
            return yaml.load(f, Loader=yaml.FullLoader)

    def get_service(self, service_name: str) -> Dict[str, Any]:
        """
        Get the full config for the service named ``service_name`` from our
        parsed YAML file.

        Args:
            service_name: the name of an ECS service listed in our YAML file under
                the ``services:`` section

        Raises:
            Config.NoSuchSectionItemError: no service named ``service_name`` existed
                in our ``services:`` section.

        Returns:
            The service config for the service named ``service_name``.
        :rtype: dict
        """
        return self.get_section_item('services', service_name)

    def get_section(self, section_name: str) -> List[Dict[str, Any]]:
        """
        Return the contents of a whole top level section from our deployfish.yml file.

        :param section_name string: The name of the top level section to search

        :rtype: dict
        """
        return self.cooked[section_name]

    def get_section_item(self, section_name: str, item_name: str) -> Dict[str, Any]:
        """
        Get an item from a top level section with 'name' equal to ``item_name``
        from our parsed ``deployfish.yml`` file.

        :param section_name string: The name of the top level section to search

        :param item_name: The name of the instance of the section
        :type item_name: string

        :rtype: dict
        """

        if section_name in self.cooked:
            for item in self.cooked[section_name]:
                if item['name'] == item_name:
                    return item
                if 'environment' in item and item['environment'] == item_name:
                    return item
        else:
            raise self.NoSuchSectionError(section_name)
        raise self.NoSuchSectionItemError(section_name, item_name)

    def get_raw_section_item(self, section_name: str, item_name: str) -> Dict[str, Any]:
        """
        Get an item from a top level section of the raw config with 'name' equal to ``item_name``
        from our parsed ``deployfish.yml`` file.

        :param section_name string: The name of the top level section to search

        :param item_name: The name of the instance of the section
        :type item_name: string

        :rtype: dict
        """
        if section_name in self.raw:
            for item in self.raw[section_name]:
                if item['name'] == item_name:
                    return item
                if 'environment' in item and item['environment'] == item_name:
                    return item
        else:
            raise self.NoSuchSectionError(section_name)
        raise self.NoSuchSectionItemError(section_name, item_name)

    def get_global_config(self, section: str) -> Dict[str, Any]:
        if 'deployfish' in self.cooked:
            if section in self.cooked['deployfish']:
                return self.cooked['deployfish'][section]
        return {}
