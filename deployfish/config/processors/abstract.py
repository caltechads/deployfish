from typing import Dict, Any, List, Union, TYPE_CHECKING

from deployfish.exceptions import (
    ConfigProcessingFailed,
    SkipConfigProcessing as BaseSkipConfigProcessing
)

if TYPE_CHECKING:
    from deployfish.config import Config


class AbstractConfigProcessor:

    class SkipConfigProcessing(BaseSkipConfigProcessing):
        pass

    class ProcessingFailed(ConfigProcessingFailed):
        pass

    REPLACEMENTS: List[str] = [
        '{name}',
        '{environment}',
        '{service-name}'
        '{cluster-name}'
    ]

    def __init__(self, config: "Config", context: Dict[str, Any]):
        self.config = config
        self.context = context
        self.deployfish_lookups: Dict[str, Any] = {}
        for section_name in self.config.processable_sections:
            self.deployfish_lookups[section_name] = {}
            section = self.config.cooked.get(section_name, {})
            for item in section:
                self.deployfish_lookups[section_name][item['name']] = {}
                self.deployfish_lookups[section_name][item['name']]['{name}'] = item['name']
                self.deployfish_lookups[section_name][item['name']]['{service-name}'] = item['name']
                self.deployfish_lookups[section_name][item['name']]['{environment}'] = item.get('environment', 'prod')
                if 'cluster' in item:
                    self.deployfish_lookups[section_name][item['name']]['{cluster-name}'] = item['cluster']

    def get_deployfish_replacements(self, section_name: str, item_name: str) -> Dict[str, str]:
        return self.deployfish_lookups[section_name][item_name]

    def replace(self, obj: Any, key: Union[str, int], value: Any, section_name: str, item_name: str) -> None:
        raise NotImplementedError

    def __process(self, obj: Any, key: Union[str, int], value: Any, section_name: str, item_name: str) -> None:
        if isinstance(value, dict):
            self.__process_dict(value, section_name, item_name)
        elif any(isinstance(value, t) for t in (list, tuple)):
            self.__process_list(value, section_name, item_name)
        elif isinstance(value, str):
            self.replace(obj, key, value, section_name, item_name)

    def __process_list(self, obj: List[Any], section_name: str, item_name: str) -> None:
        for i, value in enumerate(obj):
            self.__process(obj, i, value, section_name, item_name)

    def __process_dict(self, obj: Dict[str, Any], section_name: str, item_name: str) -> None:
        for key, value in list(obj.items()):
            self.__process(obj, key, value, section_name, item_name)

    def process(self):
        cooked = self.config.cooked
        for section_name in self.config.processable_sections:
            section = cooked.get(section_name, {})
            for item in section:
                self.__process_dict(item, section_name, item['name'])
