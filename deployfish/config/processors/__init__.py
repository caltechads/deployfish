from typing import TYPE_CHECKING, Any, Dict, List, Type

from deployfish.exceptions import ConfigProcessingFailed, SkipConfigProcessing

from .abstract import AbstractConfigProcessor
from .environment import EnvironmentConfigProcessor
from .terraform import TerraformStateConfigProcessor

if TYPE_CHECKING:
    from deployfish.config import Config


class ConfigProcessor:

    class ProcessingFailed(ConfigProcessingFailed):
        pass

    processor_classes: list[type[AbstractConfigProcessor]] = []

    @classmethod
    def register(cls, processor_class: type[AbstractConfigProcessor]) -> None:
        cls.processor_classes.append(processor_class)

    def __init__(self, config: "Config", context: dict[str, Any]):
        self.config = config
        self.context = context

    def process(self) -> None:
        for processor_class in self.processor_classes:
            try:
                current_processor = processor_class(self.config, self.context)
            except SkipConfigProcessing:
                continue
            try:
                current_processor.process()
            except ConfigProcessingFailed as e:
                raise self.ProcessingFailed(str(e))


ConfigProcessor.register(TerraformStateConfigProcessor)
ConfigProcessor.register(EnvironmentConfigProcessor)
