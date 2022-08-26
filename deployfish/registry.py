from typing import Type, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .core.adapters.abstract import Adapter  # noqa:F401


class AdapterRegistry:
    """
    A registry of adapters which consume specific data sources to configure deployfish models.
    """

    def __init__(self) -> None:
        self.adapters: Dict[str, Dict[str, Type["Adapter"]]] = {}

    def register(self, model_name: str, source: str, adapter_class: Type["Adapter"]) -> None:
        """
        Register a new Adapter class with a model and a source.

        :param model_name: the name of a deployfish model
        :param source: the identifier for the config source
        :param adapter_class: the class of the source -> model adapter to use
        """
        if model_name not in self.adapters:
            self.adapters[model_name] = {}
        self.adapters[model_name][source] = adapter_class

    def get(self, model_name: str, source: str) -> Type["Adapter"]:
        """
        Return the source -> model Adapter class to use for the source ``source`` and
        model ``model_name``.
        """
        return self.adapters[model_name][source]


importer_registry: AdapterRegistry = AdapterRegistry()
click_registry: AdapterRegistry = AdapterRegistry()
