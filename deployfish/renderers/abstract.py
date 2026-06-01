from typing import Any


class AbstractRenderer:
    """
    Render structured data into human-readable output.

    Args:
        *args: Positional renderer configuration.

    Keyword Args:
        **kwargs: Keyword renderer configuration.

    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize renderer base class.

        Args:
            *args: Positional renderer configuration.

        Keyword Args:
            **kwargs: Keyword renderer configuration.

        """

    def render(self, data: Any, **kwargs: Any) -> str:
        """
        Render provided data into a string.

        Args:
            data: Data to render.

        Keyword Args:
            **kwargs: Renderer-specific options.

        Returns:
            Human-readable output string.

        """
        raise NotImplementedError
