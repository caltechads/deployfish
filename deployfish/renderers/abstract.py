from typing import Any


class AbstractRenderer:
    """Render structured data into human-readable output."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize renderer base class."""

    def render(self, data: Any, **kwargs: Any) -> str:
        """Render provided data into a string."""
        raise NotImplementedError
