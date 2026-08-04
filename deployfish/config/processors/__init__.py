from typing import TYPE_CHECKING, Any

from deployfish.exceptions import ConfigProcessingFailed, SkipConfigProcessing

from .abstract import AbstractConfigProcessor
from .environment import EnvironmentConfigProcessor
from .terraform import TerraformStateConfigProcessor

if TYPE_CHECKING:
    from deployfish.config import Config


class ConfigProcessor:
    """
    Model config processor behavior.

    Args:
        config: config.
        context: context.

    """

    class ProcessingFailed(ConfigProcessingFailed):
        pass

    #: Processor classes.
    processor_classes: list[type[AbstractConfigProcessor]] = []

    @classmethod
    def register(cls, processor_class: type[AbstractConfigProcessor]) -> None:
        """
        Register.

        Args:
            processor_class: processor class.

        """
        cls.processor_classes.append(processor_class)

    def __init__(self, config: "Config", context: dict[str, Any]):
        #: Config.
        """
        Initialize ConfigProcessor.

        Args:
            config: config.
            context: context.

        """
        #: Config.
        self.config = config
        #: Context.
        self.context = context

    def process(self) -> None:
        """
        Process.
        """
        for processor_class in self.processor_classes:
            try:
                current_processor = processor_class(self.config, self.context)
            except SkipConfigProcessing:
                continue
            try:
                current_processor.process()
            except ConfigProcessingFailed as e:
                raise self.ProcessingFailed(str(e)) from e


ConfigProcessor.register(TerraformStateConfigProcessor)
ConfigProcessor.register(EnvironmentConfigProcessor)
