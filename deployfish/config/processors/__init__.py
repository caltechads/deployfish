from deployfish.exceptions import ConfigProcessingFailed

from .environment import EnvironmentConfigProcessor
from .terraform import TerraformStateConfigProcessor


class ConfigProcessor(object):

    class ProcessingFailed(ConfigProcessingFailed):
        pass

    processor_classes = []

    @classmethod
    def register(cls, processor_class):
        cls.processor_classes.append(processor_class)

    def __init__(self, config, context):
        self.config = config
        self.context = context

    def process(self):
        for processor_class in self.processor_classes:
            try:
                current_processor = processor_class(self.config, self.context)
            except current_processor.SkipConfigProcessing:
                continue
            try:
                current_processor.process()
            except current_processor.ProcessingFailed as e:
                raise self.ProcessingFailed(str(e))


ConfigProcessor.register(TerraformStateConfigProcessor)
ConfigProcessor.register(EnvironmentConfigProcessor)
