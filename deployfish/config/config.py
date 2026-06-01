import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Final, Literal, cast

import boto3
import click
import yaml

from deployfish.exceptions import (
    ConfigProcessingFailed,
    NoSuchConfigSection,
    NoSuchConfigSectionItem,
)

from .processors import ConfigProcessor


class Config:
    """
    Read ``deployfish.yml`` and expose interpolated config sections.

    String values in sections named by :py:attr:`processable_sections` support
    variable substitution.

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
        raw_config: If supplied, use this config data instead of loading from
            ``filename``.

    """

    class NoSuchSectionError(NoSuchConfigSection):
        pass

    class NoSuchSectionItemError(NoSuchConfigSectionItem):
        pass

    #: The default name of our config file
    DEFAULT_DEPLOYFISH_CONFIG_FILE: Final[str] = "deployfish.yml"

    #: The list of sections in our config file that will be processed
    #: by our :py:class:`deployfish.config.processors.ConfigProcessor`
    processable_sections: list[str] = ["services", "tasks", "tunnels"]
    #: Path to loaded config file.
    filename: str
    #: Raw config before interpolation.
    __raw: dict[str, Any]
    #: Cooked config after interpolation.
    __cooked: dict[str, Any]
    #: Optional boto3 session passed by callers.
    boto3_session: boto3.session.Session | None

    @classmethod
    def new(cls, **kwargs) -> "Config":
        """
        Construct and optionally interpolate a config object.

        Keyword Args:
            kwargs: Supported keys are ``filename``, ``raw_config``, and
                ``interpolate``.

        Returns:
            Initialized config object.

        Side Effects:
            May run config processors and exit process on processing failure.

        """
        filename: str = kwargs.pop("filename", cls.DEFAULT_DEPLOYFISH_CONFIG_FILE)
        if filename is None:
            filename = cls.DEFAULT_DEPLOYFISH_CONFIG_FILE
        config = cls(filename=filename, raw_config=kwargs.pop("raw_config", None))
        if kwargs.pop("interpolate", True):
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
        raw_config: dict[str, Any] | None = None,
        boto3_session: boto3.session.Session | None = None,
    ) -> None:
        """
        Initialize config state from a file path or provided payload.

        Args:
            filename: Config file path.
            raw_config: Optional preloaded config payload.
            boto3_session: Optional boto3 session reserved for callers that
                thread AWS context through config creation.

        """
        #: Path to loaded config file.
        self.filename: str = filename
        #: Optional boto3 session passed by callers.
        self.boto3_session = boto3_session
        #: Raw config before interpolation.
        self.__raw: dict[str, Any] = raw_config or self.load_config(filename)
        #: Cooked config after interpolation.
        self.__cooked: dict[str, Any] = deepcopy(self.__raw)

    @property
    def raw(self) -> dict[str, Any]:
        """
        Returns:
            The pre-interpolated version of the raw YAML.

        """
        return self.__raw

    @property
    def cooked(self) -> dict[str, Any]:
        """
        Returns:
            The post-interpolated version of the raw YAML.

        """
        return self.__cooked

    @property
    def tasks(self) -> list[dict[str, Any]]:
        """
        Return configured task entries.

        Returns:
            Task config records from cooked config.

        """
        return self.cooked.get("tasks", [])

    @property
    def services(self) -> list[dict[str, Any]]:
        """
        Return configured service entries.

        Returns:
            Service config records from cooked config.

        """
        return self.cooked.get("services", [])

    def load_config(self, filename: str) -> dict[str, Any]:
        """
        Read our deployfish.yml file from disk and return it as parsed YAML.

        Args:
            filename: the path to our deployfish.yml file

        Returns:
            Raw contents of the config file decoded to a dict.

        """
        path = Path(filename)
        if not path.exists():
            msg = f"Couldn't find deployfish config file '{filename}'"
            raise ConfigProcessingFailed(msg)
        if not path.is_file():
            msg = f"Deployfish config file '{filename}' exists but is not readable"
            raise ConfigProcessingFailed(msg)
        try:
            with path.open(encoding="utf-8") as file_obj:
                loaded = yaml.load(file_obj, Loader=yaml.FullLoader)  # noqa: S506
        except OSError as exc:
            msg = f"Deployfish config file '{filename}' exists but is not readable"
            raise ConfigProcessingFailed(msg) from exc
        return cast("dict[str, Any]", loaded)

    def get_service(self, service_name: str) -> dict[str, Any]:
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
        return self.get_section_item("services", service_name)

    def get_section(self, section_name: str) -> list[dict[str, Any]]:
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

    def get_section_item(self, section_name: str, item_name: str) -> dict[str, Any]:
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
                if item["name"] == item_name:
                    return item
                if "environment" in item and item["environment"] == item_name:
                    return item
        else:
            raise self.NoSuchSectionError(section_name)
        raise self.NoSuchSectionItemError(section_name, item_name)

    def get_raw_section_item(self, section_name: str, item_name: str) -> dict[str, Any]:
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
                if item["name"] == item_name:
                    return item
                if "environment" in item and item["environment"] == item_name:
                    return item
        else:
            raise self.NoSuchSectionError(section_name)
        raise self.NoSuchSectionItemError(section_name, item_name)

    def get_global_config(self, section: str) -> dict[str, Any]:
        """
        Return one deployfish-global config section.

        Args:
            section: Section name under ``deployfish``.

        Returns:
            Requested section dict or empty dict when absent.

        """
        if "deployfish" in self.cooked:
            if section in self.cooked["deployfish"]:
                return self.cooked["deployfish"][section]
        return {}

    def set_global_config(self, section: str, key: str, value: Any) -> None:
        """
        Set one key in global deployfish config.

        Args:
            section: Section name under ``deployfish``.
            key: Key inside the section.
            value: Value to assign.

        Side Effects:
            Mutates cooked config in memory.

        """
        if "deployfish" not in self.cooked:
            self.cooked["deployfish"] = {}
        if section not in self.cooked["deployfish"]:
            self.cooked["deployfish"][section] = {}
        self.cooked["deployfish"][section][key] = value

    @property
    def ssh_provider_type(self) -> Literal["bastion", "ssm"]:
        """
        Return configured SSH proxy provider.

        Returns:
            SSH provider type string.

        """
        ssh_config = self.get_global_config("ssh")
        return cast('Literal["bastion", "ssm"]', ssh_config.get("proxy"))

    @ssh_provider_type.setter
    def ssh_provider_type(self, value: Literal["bastion", "ssm"]) -> None:
        """
        Set configured SSH proxy provider.

        Args:
            value: New SSH provider type.

        Raises:
            ValueError: Provider type is not supported.

        """
        if value not in ["bastion", "ssm"]:
            msg = (
                f"Invalid SSH provider type: {value}. "
                "Valid values are 'bastion' and 'ssm'"
            )
            raise ValueError(msg)
        self.set_global_config("ssh", "proxy", value)
