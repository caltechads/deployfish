from typing import Dict, Any, List, Callable, Tuple

from deployfish.exceptions import SchemaException as BaseSchemaException


class Adapter:
    """
    Given a dict of data from a data source, convert it appropriate data structures to be used
    to initialize a deployfish model.

    Minimally this means translating the source data into the data structure returned by an
    apporpriate ``describe_*`` AWS API call.  In more complicated cases, there may be additional
    data returned also.
    """

    NONE: str = 'deployfish:required'

    class SchemaException(BaseSchemaException):
        """
        Raise this if data in the config source does not validate properly.
        """
        pass

    def __init__(self, data: Dict[str, Any], partial: bool = False, **kwargs) -> None:
        """
        ``data`` is the raw data from our source.
        """
        self.data: Dict[str, Any] = data
        self.partial: bool = partial

    def only_one_is_True(self, data: List[bool]) -> bool:
        """
        Look through the list ``data``, a list of boolean values, and return True if only one True is in the
        list, False otherwise.
        """
        # FIXME: much better ways to do this
        true_found = False
        for v in data:
            if v and not true_found:
                true_found = True
            elif v and true_found:
                return False  # "Too Many Trues"
        return true_found

    def set(
        self,
        data: Dict[str, Any],
        source_key: str,
        dest_key: str = None,
        default: Any = NONE,
        optional: bool = False,
        convert: Callable = None
    ):
        if dest_key is None:
            dest_key = source_key
        if self.partial or optional:
            if source_key in self.data:
                data[dest_key] = self.data[source_key]
        else:
            if default != self.NONE:
                data[dest_key] = self.data.get(source_key, default)
            else:
                data[dest_key] = self.data[source_key]
        if dest_key in data and convert:
            data[dest_key] = convert(data[dest_key])

    def convert(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        This method is the meat of the adapter -- it is what takes ``self.data`` and returns the
        data structures needed to initialize our model.

        The return type varies by what the model needs.
        """
        raise NotImplementedError
