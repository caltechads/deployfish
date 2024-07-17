from copy import deepcopy
import os
import sys
from typing import Dict, Any, List, Literal, cast
try:
    from typing import Final
except ImportError:
    from typing_extensions import Final  # type: ignore
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

    @classmethod
    def add_processable_section(cls, section_name: str) -> None:
        """
        Add the name of a processable section -- one in which we can do
        intepolations.   This exists so that plugins can add their sections
        to those that are processable.

        Args:
            section_name: the name of the section to add
        """
        if section_name not in cls.processable_sections:
            cls.processable_sections.append(section_name)

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
        Returns:
            The pre-interpolated version of the raw YAML.
        """
        return self.__raw

    @property
    def cooked(self) -> Dict[str, Any]:
        """
        Returns:
            The post-interpolated version of the raw YAML.
        """
        return self.__cooked

    @property
    def tasks(self) -> List[Dict[str, Any]]:
        return self.cooked.get('tasks', [])

    @property
    def services(self) -> List[Dict[str, Any]]:
        return self.cooked.get('services', [])

    def load_config(self, filename: str) -> Dict[str, Any]:
        """
        Read our deployfish.yml file from disk and return it as parsed YAML.

        Args:
            filename: the path to our deployfish.yml file

        Return:
            The raw contents of the deployfish.yml file decoded to a dict
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
            service_name: the name of an ECS service listed in our YAML file
                under the ``services:`` section

        Raises:
            Config.NoSuchSectionItemError: no service named ``service_name``
                existed in our ``services:`` section.

        Returns:
            The service config for the service named ``service_name``.
        """
        return self.get_section_item('services', service_name)

    def get_section(self, section_name: str) -> List[Dict[str, Any]]:
        """
        Return the contents of a whole top level section from our deployfish.yml
        file.

        Args:
            section_name: The name of the top level section to retrieve

        Raises:
            KeyError: no section named ``section_name`` exists in the config.

        Returns:
            The post-interpolation contents of the section named ``section_name``.
        """
        return self.cooked[section_name]

    def get_section_item(self, section_name: str, item_name: str) -> Dict[str, Any]:
        """
        Get an item from a top level section with ``name`` equal to
        ``item_name`` from our INTERPOLATED deployfish.yml file.

        Item name can be either the ``name`` of the item, or the ``environment``
        of the item.

        .. note::
            If you have several items with the same ``environment``, and you ask
            for the config for the item with ``item_name`` set to that
            environment, you'll get the first one in the file.

        Args:
            section_name: The name of the top level section to retrieve
            item_name: The name of the instance of the section

        Raises:
            Config.NoSuchSectionError: no section named ``section_name`` exists
                in the config
            Config.NoSuchSectionItemError: no item named  ``item_name`` exists
                in the section named ``section_name``

        Returns:
            The contents of the entry named ``item_name`` in the section named
            ``section_name`` from the post-interpolation version of the config.
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
        Get an item from a top level section with ``name`` equal to
        ``item_name`` from our RAW deployfish.yml file.

        Item name can be either the ``name`` of the item, or the ``environment``
        of the item.

        .. note::
            If you have several items with the same ``environment``, and you ask
            for the config for the item with ``item_name`` set to that
            environment, you'll get the first one in the file.

        Args:
            section_name: The name of the top level section to retrieve
            item_name: The name of the instance of the section

        Raises:
            Config.NoSuchSectionError: no section named ``section_name`` exists
                in the config
            Config.NoSuchSectionItemError: no item named  ``item_name`` exists
                in the section named ``section_name``

        Returns:
            The contents of the entry named ``item_name`` in the section named
            ``section_name`` from the pre-interpolation version of the config.
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

    def set_global_config(self, section: str, key: str, value: Any) -> None:
        if 'deployfish' not in self.cooked:
            self.cooked['deployfish'] = {}
        if section not in self.cooked['deployfish']:
            self.cooked['deployfish'][section] = {}
        self.cooked['deployfish'][section][key] = value

    @property
    def ssh_provider_type(self) -> Literal["bastion", "ssm"]:
        """
        A shortcut method to figure out what SSH provider we're using.

        """
        ssh_config = self.get_global_config('ssh')
        return cast(Literal["bastion", "ssm"], ssh_config.get('proxy'))

    @ssh_provider_type.setter
    def ssh_provider_type(self, value: Literal["bastion", "ssm"]) -> None:
        """
        A shortcut method to set what SSH provider we're using.

        Args:
            value: the new SSH provider type.  Must be either 'bastion' or 'ssm'.
        """
        assert value in ['bastion', 'ssm'], \
            f"Invalid SSH provider type: {value}.  Valid values are 'bastion' and 'ssm'"
        self.set_global_config('ssh', 'proxy', value)
