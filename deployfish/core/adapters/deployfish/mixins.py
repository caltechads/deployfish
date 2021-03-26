from deployfish.exceptions import SchemaException

from ..abstract import Adapter


class DeployfishYamlAdapter(Adapter):

    class SchemaException(SchemaException):
        pass
