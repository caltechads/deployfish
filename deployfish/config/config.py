from copy import deepcopy, copy
import os
import sys

import click
import yaml

from deployfish.exceptions import ConfigProcessingFailed
from deployfish.core.aws import build_boto3_session
from .processors import ConfigProcessor


class Config(object):

    """
    This class reads our ``deployfish.yml`` file and handles the allowed
    variable substitutions in string values for service entries under the
    ``services:`` section.

    Allowed variable substitutions:

    * ``${terraform.<lookup key>}``:  If we have a ``terraform:`` section
      in our YAML, replace this with the terraform lookup value for
      ``<lookup key>``.

    * ``${env.<environment var>}```:  If the environment variable
      ``<environment var>`` exists in our environment, replace this with
      the value of that environment variable.
    """

    DEFAULT_DEPLOYFISH_CONFIG_FILE = 'deployfish.yml'

    processable_sections = [
        'services',
        'tasks'
    ]

    @classmethod
    def new(cls, **kwargs):
        filename = kwargs.pop('filename', cls.DEFAULT_DEPLOYFISH_CONFIG_FILE)
        if filename is None:
            filename = cls.DEFAULT_DEPLOYFISH_CONFIG_FILE
        config = cls(
            filename=filename,
            use_aws_section=kwargs.pop('use_aws_section', True),
            raw_config=kwargs.pop('raw_config', None),
            boto3_session=kwargs.pop('boto3_session', None)
        )
        if kwargs.pop('interpolate', True):
            try:
                processor = ConfigProcessor(config, kwargs)
                processor.process()
            except ConfigProcessingFailed as e:
                click.secho(str(e))
                sys.exit(1)
        return config

    def __init__(self, filename, use_aws_section=True, raw_config=None, boto3_session=None):
        self.filename = filename
        self.__raw = raw_config if raw_config else self.load_config(filename)
        self.__cooked = deepcopy(self.__raw)
        if use_aws_section:
            build_boto3_session(config=self, boto3_session_override=boto3_session)
        else:
            build_boto3_session(boto3_session_override=boto3_session)

    @property
    def raw(self):
        return self.__raw

    @property
    def cooked(self):
        return self.__cooked

    @property
    def tasks(self):
        return self.cooked['tasks']

    @property
    def services(self):
        return self.cooked['services']

    def load_config(self, filename):
        """
        Read our deployfish.yml file from disk and return it as parsed YAML.

        :param filename: the path to our deployfish.yml file
        :type filename: string

        :rtype: dict
        """
        if not os.path.exists(filename):
            raise ConfigProcessingFailed("Couldn't find deployfish config file '{}'".format(filename))
        elif not os.access(filename, os.R_OK):
            raise ConfigProcessingFailed(
                "Deployfish config file '{}' exists but is not readable".format(filename)
            )
        with open(filename) as f:
            return yaml.load(f, Loader=yaml.FullLoader)

    def get_service(self, service_name):
        """
        Get the full config for the service named ``service_name`` from our
        parsed YAML file.

        :param service_name string: the name of an ECS service listed in our YAML
                             file under the ``services:`` section

        :rtype: dict
        """
        return self.get_section_item('services', service_name)

    def get_section(self, section_name):
        """
        Return the contents of a whole top level section from our deployfish.yml file.

        :param section_name string: The name of the top level section to search

        :rtype: dict
        """
        return self.cooked[section_name]

    def get_section_item(self, section_name, item_name):
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
                elif 'environment' in item and item['environment'] == item_name:
                    return item
        raise KeyError

    def get_raw_section_item(self, section_name, item_name):
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
                elif 'environment' in item and item['environment'] == item_name:
                    return item
        raise KeyError

    def get_global_config(self, section):
        if 'deployfish' in self.cooked:
            if section in self.cooked['deployfish']:
                return self.cooked['deployfish'][section]
        return None
