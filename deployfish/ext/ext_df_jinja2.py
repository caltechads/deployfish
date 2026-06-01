from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import click
from cement.core.output import OutputHandler
from cement.ext.ext_jinja2 import Jinja2OutputHandler, Jinja2TemplateHandler
from cement.utils.misc import minimal_logger

from deployfish.renderers import (
    LBListenerTableRenderer,
    TableRenderer,
    TargetGroupTableRenderer,
)
from deployfish.renderers.misc import target_group_listener_rules

#: Logger used by Cement Jinja2 extension hooks.
LOG = minimal_logger(__name__)


def color(value: str, **kwargs) -> str:
    """
    Render string with ``click.style``.

    Args:
        value: Value to colorize.

    Keyword Args:
        **kwargs: Keyword arguments forwarded to ``click.style``.

    Returns:
        Styled string.

    """
    return click.style(str(value), **kwargs)


def section_title(value: str, **kwargs) -> str:
    """
    Render a section title from ``value``.  This looks like:

        value
        -----

    with optional click font manipulation for ``value``.

    Args:
        value: Title text to render.

    Keyword Args:
        **kwargs: Keyword arguments forwarded to ``click.style``.

    Returns:
        Rendered title and underline block.

    """
    if "fg" not in kwargs:
        kwargs["fg"] = "cyan"
    lines = [
        click.style(str(value), **kwargs),
        click.style("-" * len(value), **kwargs),
    ]
    return "\n".join(lines)


def fromtimestamp(data: float, **_: Any) -> str:
    """
    Convert Unix epoch timestamp to UTC datetime text.

    Args:
        data: Epoch timestamp in seconds or milliseconds.

    Keyword Args:
        **_: Ignored filter keyword arguments from Jinja.

    Returns:
        Formatted UTC timestamp string.

    """
    try:
        return datetime.fromtimestamp(data, UTC).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        # This is an AWS timestamp with microseconds
        return datetime.fromtimestamp(data / 1000.0, UTC).strftime(
            "%Y-%m-%d %H:%M:%S"
        )


def tabular(data: Sequence[Any], **kwargs: Any) -> str:
    """
    Render sequence with ``TableRenderer``.

    ``kwargs`` describe columns plus renderer options. Column keyword names
    become headers after underscores are converted to spaces.

    Args:
        data: Row objects to render.

    Keyword Args:
        **kwargs: Column mappings and renderer options like ``ordering``,
            ``date_format``, ``datetime_format``, ``float_precision``,
            ``tablefmt``, and ``show_headers``.

    Returns:
        Rendered table string.

    """
    renderer_kwargs: dict[str, Any] = {}
    columns: dict[str, Any] = {}
    for key, value in list(kwargs.items()):
        if key in [
            "ordering",
            "date_format",
            "datetime_format",
            "float_precision",
            "tablefmt",
            "show_headers",
        ]:
            renderer_kwargs[key] = value
        elif key.endswith("_datatype"):
            column_name = key.replace("_datatype", "").replace("_", " ")
            if column_name not in columns:
                columns[column_name] = {}
            columns[column_name]["datatype"] = value
        elif key.endswith("_default"):
            column_name = key.replace("_default", "").replace("_", " ")
            if column_name not in columns:
                columns[column_name] = {}
            columns[column_name]["default"] = value
        else:
            column_name = key.replace("_", " ")
            if column_name not in columns:
                columns[column_name] = {}
            columns[column_name]["key"] = value

    renderer = TableRenderer(columns, **renderer_kwargs)
    return renderer.render(data)


def target_group_table(data: Sequence[Any]) -> str:
    """
    Render table for target groups.

    Args:
        data: Target-group-like row objects.

    Returns:
        Rendered table string.

    """
    columns = {
        "Name": "name",
        "LB Port": "listener_port",
        "Rules": "rules",
        "Target Port": "container_port",
        "Targets": "targets",
    }
    renderer = TargetGroupTableRenderer(columns)
    return renderer.render(data)


def lb_listener_table(data: Sequence[Any]) -> str:
    """
    Render table for ELBv2 listeners.

    Args:
        data: Listener-like row objects.

    Returns:
        Rendered table string.

    """
    columns = {
        "Port": "port",
        "Protocol": "protocol",
        "Default Actions": "default_action",
        "# Rules": "rules",
        "Certificates": "certificates",
    }
    renderer = LBListenerTableRenderer(columns)
    return renderer.render(data)

class DeployfishJinja2OutputHandler(Jinja2OutputHandler):
    """
    We're subclassing the cement Jinja2OutputHandler here so we can use our own
    jinja2 template handler instead of the cement default one.
    """

    class Meta:
        label = "df_jinja2"

    def _setup(self, app: Any) -> None:
        """
        Bind custom template handler.

        Args:
            app: Cement application instance.

        Side Effects:
            Resolves and stores template handler on output handler.

        """
        OutputHandler._setup(self, app)  # pylint: disable=protected-access
        self.templater = self.app.handler.resolve("template", "df_jinja2", setup=True)


class DeployfishJinja2TemplateHandler(Jinja2TemplateHandler):
    """
    We're subclassing the cement Jinja2TemplateHandler here so we can add some
    custom filters.
    """

    class Meta:
        label = "df_jinja2"

    def load(self, *args: Any, **kwargs: Any) -> tuple[Any, Any, Any]:
        """
        Load template content and register custom filters.

        Args:
            *args: Positional arguments forwarded to Cement loader.

        Keyword Args:
            **kwargs: Keyword arguments forwarded to Cement loader.

        Returns:
            Loaded template content tuple.

        Side Effects:
            Registers custom filters on Jinja environment.

        """
        content, _type, _path = super().load(*args, **kwargs)
        self.env.filters["color"] = color
        self.env.filters["section_title"] = section_title
        self.env.filters["fromtimestamp"] = fromtimestamp
        self.env.filters["lb_listener_table"] = lb_listener_table
        self.env.filters["target_group_table"] = target_group_table
        self.env.filters["target_group_listener_rules"] = target_group_listener_rules
        self.env.filters["tabular"] = tabular
        return content, _type, _path


def load(app: Any) -> None:
    """
    Register deployfish Jinja2 handlers with Cement app.

    Args:
        app: Cement application instance.

    Side Effects:
        Registers output and template handlers.

    """
    app.handler.register(DeployfishJinja2OutputHandler)
    app.handler.register(DeployfishJinja2TemplateHandler)
