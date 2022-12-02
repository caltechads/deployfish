from typing import Dict, Any, List, Union, TYPE_CHECKING

from deployfish.exceptions import (
    ConfigProcessingFailed,
    SkipConfigProcessing as BaseSkipConfigProcessing
)

if TYPE_CHECKING:
    from deployfish.config import Config


class AbstractConfigProcessor:
    """
    A base class for processors for our our ``deployfish.yml`` file.  These
    processors modify the ``deployfish.yml`` file contents in some way before
    the rest of ``deployfish`` consumes it.

    Args:
        config: the :py:class:`deployfish.config.Config` object we're working
            with
        context: a dict of additional data that we might use when processing the
            config
    """

    class SkipConfigProcessing(BaseSkipConfigProcessing):
        pass

    class ProcessingFailed(ConfigProcessingFailed):
        pass

    #: The list of base deployfish replacement strings we currently support
    REPLACEMENTS: List[str] = [
        '{name}',
        '{environment}',
        '{service-name}',
        '{task-name}',
        '{cluster-name}'
    ]

    def __init__(self, config: "Config", context: Dict[str, Any]):
        #: The :py:class:`deployfish.config.Config` we are processing
        self.config = config
        #: Any additional context our caller wished to give us for our processing
        self.context = context
        #: This holds values for each appropriate replacement in :py:attr:`REPLACEMENTS`
        #: for each item in each section listed in
        #: :py:attr:`deployfish.config.Config.processable_sections`
        self.deployfish_lookups: Dict[str, Any] = {}
        self.extract_replacements()

    def extract_replacements(self) -> None:
        """
        Populate :py:attr:`deployfish_lookups`.
        """
        for section_name in self.config.processable_sections:
            self.deployfish_lookups[section_name] = {}
            section = self.config.cooked.get(section_name, {})
            for item in section:
                self.deployfish_lookups[section_name][item['name']] = {}
                self.deployfish_lookups[section_name][item['name']]['{name}'] = item['name']
                if section_name == 'services':
                    self.deployfish_lookups[section_name][item['name']]['{service-name}'] = item['name']
                if section_name == 'tasks':
                    self.deployfish_lookups[section_name][item['name']]['{task-name}'] = item['name']
                self.deployfish_lookups[section_name][item['name']]['{environment}'] = item.get('environment', 'prod')
                if 'cluster' in item:
                    self.deployfish_lookups[section_name][item['name']]['{cluster-name}'] = item['cluster']

    def get_deployfish_replacements(self, section_name: str, item_name: str) -> Dict[str, str]:
        """
        Return all known replacements for ``deployfish.yml`` section name
        ``section_name``, item name ``item_name``.

        Example::

            If we have a ``services`` entry like this::

                services:
                    - name: foobar-test
                      environment: test
                      cluster_name: foobar-cluster

            and we do::

                processor.get_deployfish_replacement('services', 'foobar-test')

            we get back::

                {
                    '{name}': 'foobar-test',
                    '{service-name}': 'foobar-test',
                    '{environment}': 'test',
                    '{cluster-name}': 'foobar-cluster',
                }

        Args:
            section_name: the name of the top level section in ``deployfish.yml``
            item_name: the name of the item in ``section_name``

        Raises:
            KeyError: we have no replacements for either ``section_name`` or ``item_name``

        Returns:
            The replacements for ``section_name``, ``item_name``.
        """
        return self.deployfish_lookups[section_name][item_name]

    def replace(
        self,
        obj: Union[List, Dict],
        key: Union[str, int],
        value: str,
        section_name: str,
        item_name: str
    ) -> None:
        """
        Perform string replacements on ``value``, a string value in our
        ``deployfish.yml`` item.

        Args:
            obj: a list or dict from an item from a ``deployfish.yml``
            key: the name of the key (if ``obj`` is a dict) or index (if ``obj``
                is a list``) in ``obj``
            value: our string value from ``obj[key]``
            section_name: the section name ``obj`` came from
            item_name: the name of the item in ``section_name`` that ``obj``
                came from
        """
        raise NotImplementedError

    def __process(
        self,
        obj: Any,
        key: Union[str, int],
        value: Any,
        section_name: str,
        item_name: str
    ) -> None:
        """
        Process ``obj``, a value from a key of an item from ``deployfish.yml``,
        looking for strings on which to do string replacements.

        If ``obj`` is a list or a dictionary, recurse into it.

        If ``obj`` is a string, do the string replacements on ``obj``.

        If ``obj`` is none of the above (an int or float), do nothing.

        Args:
            obj: a value from an item from a ``deployfish.yml``
            key: the name of the key (if ``obj`` is a dict) or index (if ``obj``
                is a list``) in ``obj``
            value: the value of ``obj[key]``
            section_name: the section name ``obj`` came from
            item_name: the name of the item in ``section_name`` that ``obj``
                came from
        """
        if isinstance(value, dict):
            self.__process_dict(value, section_name, item_name)
        elif any(isinstance(value, t) for t in (list, tuple)):
            self.__process_list(value, section_name, item_name)
        elif isinstance(value, str):
            self.replace(obj, key, value, section_name, item_name)

    def __process_list(self, obj: List[Any], section_name: str, item_name: str) -> None:
        """
        Process ``obj``, a list value of an item from ``deployfish.yml``,
        looking for strings on which to do string replacements.

        Args:
            obj: a value from an item from a ``deployfish.yml``
            section_name: the section name ``obj`` came from
            item_name: the name of the item in ``section_name`` that ``obj``
                came from
        """
        for i, value in enumerate(obj):
            self.__process(obj, i, value, section_name, item_name)

    def __process_dict(self, obj: Dict[str, Any], section_name: str, item_name: str) -> None:
        """
        Recurse through each key in our dict ``obj`` and process it
        appropriately.  We need to get down to individual strings before we can
        do any replacements

        Args:
            obj: the dictionary to act on
            section_name: the section name this dictionary came from
            item_name: the name of the item in ``section_name`` this dictionary
                came from
        """

        for key, value in list(obj.items()):
            self.__process(obj, key, value, section_name, item_name)

    def process(self):
        """
        This is the method that :py:class:`ConfigProcessor` will execute as it
        loops through known processors.

        :py:attr:`deployfish.config.Config.processable_sections`` and run our
        processors on all items in those sections.  Save the fully processed
        version of our ``deployfish.yml`` data in
        :py:attr:`deployfish.config.Config.cooked`.

        Raises:
            AbstractConfigProcessor.ProcessingFailed: something went wrong when
                we tried to run
            AbstractConfigProcessor.SkipConfigProcessing: we didn't run
        """
        cooked = self.config.cooked
        for section_name in self.config.processable_sections:
            section = cooked.get(section_name, {})
            for item in section:
                # Assume each item in a section is s dict
                self.__process_dict(item, section_name, item['name'])
