from collections.abc import Callable
from typing import Any

from deployfish.exceptions import SchemaException as BaseSchemaException


class Adapter:
    """
    Given a dict of data from a data source, convert it appropriate data

    Args:
        data: data.
        partial: partial.

    """

    #: None.
    NONE: str = "deployfish:required"

    class SchemaException(BaseSchemaException):
        """
        Raise this if data in the config source does not validate properly.
        """

    def __init__(
        self,
        data: dict[str, Any],
        partial: bool = False,  # noqa: FBT001, FBT002
        **_kwargs: Any,
    ) -> None:
        """
        Initialize adapter with raw source data.

        Args:
            data: Raw source data to adapt.
            partial: Whether partial source payloads are allowed.

        Keyword Args:
            _kwargs: kwargs.

        """
        #: Data.
        self.data: dict[str, Any] = data
        #: Partial.
        self.partial: bool = partial

    def only_one_is_True(self, data: list[bool]) -> bool:  # noqa: N802
        """
        Return whether exactly one value in ``data`` is truthy.

        Args:
            data: Boolean values to inspect.

        Returns:
            ``True`` when exactly one value is truthy.

        """
        return sum(data) == 1

    def set(  # noqa: PLR0913
        self,
        data: dict[str, Any],
        source_key: str,
        dest_key: str | None = None,
        default: Any = NONE,
        optional: bool = False,  # noqa: FBT001, FBT002
        convert: Callable[[Any], Any] | None = None,
    ) -> None:
        """
        Copy one source value into output payload.

        Args:
            data: Destination payload being built.
            source_key: Key to read from source data.
            dest_key: Key to write in destination payload.
            default: Fallback value when source key is missing.
            optional: Whether missing source keys are allowed.
            convert: Optional converter for copied values.

        Side Effects:
            Mutates ``data`` in place.

        """
        if dest_key is None:
            dest_key = source_key
        if self.partial or optional:
            if source_key in self.data:
                data[dest_key] = self.data[source_key]
        elif default != self.NONE:
            data[dest_key] = self.data.get(source_key, default)
        else:
            data[dest_key] = self.data[source_key]
        if dest_key in data and convert is not None:
            data[dest_key] = convert(data[dest_key])

    def convert(self) -> tuple[Any, Any]:
        """
        Convert source payload into model constructor inputs.

        Returns:
            Tuple of adapted model data and keyword arguments.

        """
        raise NotImplementedError
