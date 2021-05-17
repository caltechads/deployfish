class AdapterRegistry(object):

    def __init__(self):
        self.adapters = {}

    def register(self, model_name, source, adapter_class):
        if model_name not in self.adapters:
            self.adapters[model_name] = {}
        self.adapters[model_name][source] = adapter_class

    def get(self, model_name, source):
        return self.adapters[model_name][source]


importer_registry = AdapterRegistry()
click_registry = AdapterRegistry()
