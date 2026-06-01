import datetime
from copy import deepcopy
from textwrap import wrap
from typing import Any, cast

import click
from tabulate import tabulate

from deployfish.core.models import LoadBalancerListener, TargetGroup
from deployfish.exceptions import RenderException

from .abstract import AbstractRenderer
from .misc import target_group_listener_rules

# ========================
# Renderers
# ========================


class TableRenderer(AbstractRenderer):
    """
    Render a list of results as an ASCII table.

    Args:
        columns: Column configuration keyed by header label.
        datetime_format: Override for ``datetime.datetime`` rendering.
        date_format: Override for ``datetime.date`` rendering.
        float_precision: Override for float rendering precision.
        ordering: Optional header name to sort by. Prefix with ``-`` for desc.
        tablefmt: Output style passed to ``tabulate``.
        show_headers: Whether to include header row in output.

    """

    #: Default format for ``datetime.datetime`` values.
    DEFAULT_DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    #: Default format for ``datetime.date`` values.
    DEFAULT_DATE_FORMAT: str = "%Y-%m-%d"
    #: Default decimal precision for floats.
    DEFAULT_FLOAT_PRECISION: int = 2
    #: Base used when scaling byte magnitudes.
    BYTE_SCALE: float = 1024.0

    def __init__(  # noqa: PLR0913
        self,
        columns: dict[str, Any],
        datetime_format: str | None = None,
        date_format: str | None = None,
        float_precision: int | None = None,
        ordering: str | None = None,
        tablefmt: str = "simple",
        show_headers: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        """
        Initialize table renderer.

        Args:
            columns: Column configuration keyed by output header.
            datetime_format: Override for datetime rendering.
            date_format: Override for date rendering.
            float_precision: Override for float rendering precision.
            ordering: Optional header used for sorting.
            tablefmt: Table format string passed to ``tabulate``.
            show_headers: Whether to include table headers.

        Raises:
            AssertionError: ``columns`` was not a dict.

        """
        super().__init__()
        if not isinstance(columns, dict):
            msg = "TableRenderer: `columns` parameter to __init__ should be a dict"
            raise TypeError(msg)

        #: Ordered column descriptors used when rendering rows.
        self.columns: list[str] = list(columns.values())
        #: Header labels passed to ``tabulate``.
        self.headers: list[str] = list(columns.keys())
        #: Datetime output format.
        self.datetime_format: str = datetime_format or self.DEFAULT_DATETIME_FORMAT
        #: Date output format.
        self.date_format: str = date_format or self.DEFAULT_DATE_FORMAT
        #: Float precision used by ``float_format``.
        self.float_precision: int = float_precision or self.DEFAULT_FLOAT_PRECISION
        #: Cached format string for floats.
        self.float_format: str = f"{{:.{self.float_precision}f}}"
        #: Optional header used for sorting.
        self.ordering: str | None = ordering
        #: Output format passed to ``tabulate``.
        self.tablefmt: str = tablefmt
        #: Whether rendered table includes headers.
        self.show_headers: bool = show_headers

    def get_value(self, obj: Any, column: dict[str, str] | str) -> Any:
        """
        Dereference one column from an object or rendered mapping.

        Args:
            obj: Source object or mapping.
            column: Column definition or key.

        Returns:
            Raw column value.

        Raises:
            RenderException: Column cannot be dereferenced.

        """
        data_key = column["key"] if isinstance(column, dict) else column
        try:
            return getattr(obj, data_key)
        except AttributeError:
            try:
                return obj.render_for_display()[data_key]
            except KeyError:
                pass
            except AttributeError:
                # Bare dicts do not implement ``render_for_display``.
                try:
                    return obj[data_key]
                except KeyError:
                    pass
        if isinstance(column, dict):
            if "default" in column:
                return column["default"]
        raise RenderException(
            click.style(
                f'\n\n{self.__class__.__name__}: Could not dereference "{data_key}"',
                fg="red",
            )
        )

    def human_bytes(self, value: float, suffix: str = "B") -> str:
        """
        Render byte count into human-readable units.

        Args:
            value: Byte count to format.
            suffix: Unit suffix to append.

        Returns:
            Human-readable byte string.

        """
        for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
            if abs(value) < self.BYTE_SCALE:
                return f"{value:3.1f}{unit}{suffix}"
            value /= self.BYTE_SCALE
        return "{:.1f}{}{}".format(value, "Yi", suffix)

    def _default_cast(self, value: Any) -> str:
        """
        Render values using builtin datatype formatting rules.

        Args:
            value: Value to normalize.

        Returns:
            Normalized value ready for string rendering.

        """
        if isinstance(value, datetime.datetime):
            value = value.strftime(self.datetime_format)
        elif isinstance(value, datetime.date):
            value = value.strftime(self.date_format)
        elif isinstance(value, float):
            value = self.float_format.format(value)
        return value

    def cast_column(self, _obj: Any, value: Any, column: dict[str, str] | str) -> str:
        """
        Reformat one value into a more human-friendly form.

        Args:
            obj: Source object being rendered.
            value: Raw value extracted from ``obj``.
            column: Column definition describing any special casting.

        Returns:
            Renderable string value.

        """
        if value == "":
            return value
        if isinstance(column, dict):
            if "length" in column:
                return str(len(value))
            if "datatype" not in column:
                value = self._default_cast(value)
            elif column["datatype"] == "timestamp":
                value = int(value)
                try:
                    value = datetime.datetime.fromtimestamp(
                        value, datetime.UTC
                    ).strftime(self.datetime_format)
                except ValueError:
                    # This is an AWS timestamp in milliseconds, not seconds
                    value = datetime.datetime.fromtimestamp(
                        value / 1000.0, datetime.UTC
                    ).strftime(self.datetime_format)
                value = self._default_cast(value)
            elif column["datatype"] == "bytes":
                value = int(value)
                value = self.human_bytes(value)
            if "wrap" in column:
                value = str(value)
                value = "\n".join(wrap(value, cast("int", column["wrap"])))
        return value

    def render_column(self, obj: Any, column: dict[str, str] | str) -> str:
        """
        Render one column value for one row object.

        Args:
            obj: Source object for the current row.
            column: Column definition or attribute key.

        Returns:
            Rendered column text.

        """
        key = column["key"] if isinstance(column, dict) else column
        if hasattr(self, f"render_{column}_value"):
            value = getattr(self, f"render_{column}_value")(obj, key, column)
        else:
            if "__" in key:
                refs = key.split("__")
                ref: str | None = refs.pop(0)
                while ref:
                    if isinstance(column, dict):
                        sub_column = cast("dict[str, Any]", deepcopy(column))
                        sub_column["key"] = ref
                        obj = self.get_value(obj, sub_column)
                    else:
                        obj = self.get_value(obj, ref)
                    try:
                        ref = refs.pop(0)
                    except IndexError:
                        ref = None
                value = obj  # the last one should be the value we're looking for
                return self.cast_column(obj, value, column)
            value = self.get_value(obj, column)
            value = self.cast_column(obj, value, column)
        return value

    def render(self, data: Any, **_: Any) -> str:
        """
        Render all rows into a formatted table string.

        Args:
            data: Sequence of row-like objects.

        Keyword Args:
            **_: Ignored renderer override parameters for interface parity.

        Returns:
            Formatted table output.

        """
        data = cast("list[Any]", data)
        table = []
        for obj in data:
            row = [self.render_column(obj, column) for column in self.columns]
            table.append(row)
        if self.ordering:
            reverse = False
            order_column = self.ordering
            if order_column.startswith("-"):
                reverse = True
                order_column = order_column[1:]
            order_index = self.headers.index(order_column)
            table = sorted(table, key=lambda x: x[order_index])
            if reverse:
                table.reverse()

        if self.show_headers:
            return tabulate(table, headers=self.headers, tablefmt=self.tablefmt)
        return tabulate(table, tablefmt=self.tablefmt)


class TargetGroupTableRenderer(TableRenderer):
    """Specialized renderer for ECS target groups."""

    def render_load_balancers_value(
        self,
        obj: TargetGroup,
        _key: str,
        _column: dict[str, str] | str,
    ) -> str:
        """
        Render attached load balancer names.

        Args:
            obj: Target group being rendered.
            _key: Unused renderer hook key.
            _column: Unused renderer hook column.

        Returns:
            Newline-joined load balancer names.

        """
        load_balancer_names = [lb.name for lb in obj.load_balancers]
        return "\n".join(load_balancer_names)

    def render_targets_value(
        self, obj: TargetGroup, _key: str, _column: dict[str, str] | str
    ) -> str:
        """
        Render target names.

        Args:
            obj: Target group being rendered.
            _key: Unused renderer hook key.
            _column: Unused renderer hook column.

        Returns:
            Newline-joined target names.

        """
        target_names = [t.target.name for t in obj.targets]
        return "\n".join(target_names)

    def render_rules_value(
        self, obj: TargetGroup, _key: str, _column: dict[str, str] | str
    ) -> str:
        """
        Render listener rules attached to target group.

        Args:
            obj: Target group being rendered.
            _key: Unused renderer hook key.
            _column: Unused renderer hook column.

        Returns:
            Listener rule summary string.

        """
        return target_group_listener_rules(obj)

    def render_listener_port_value(
        self,
        obj: TargetGroup,
        _key: str,
        _column: dict[str, str] | str,
    ) -> str:
        """
        Render listener protocol/port pairs.

        Args:
            obj: Target group being rendered.
            _key: Unused renderer hook key.
            _column: Unused renderer hook column.

        Returns:
            Newline-joined protocol/port strings.

        """
        return "\n".join(
            f"{listener.protocol}:{listener.port!s}" for listener in obj.listeners
        )

    def render_container_port_value(
        self,
        obj: TargetGroup,
        _key: str,
        _column: dict[str, str] | str,
    ) -> str:
        """
        Render backing container protocol/port pair.

        Args:
            obj: Target group being rendered.
            _key: Unused renderer hook key.
            _column: Unused renderer hook column.

        Returns:
            Container protocol/port string.

        """
        return "{}:{}".format(obj.data["Protocol"], obj.data["Port"])


class LBListenerTableRenderer(TableRenderer):
    """Specialized renderer for load balancer listeners."""

    def render_default_action_value(
        self,
        obj: LoadBalancerListener,
        _key: str,
        _column: dict[str, str] | str,
    ) -> str:
        """
        Render default listener actions.

        Args:
            obj: Listener being rendered.
            _key: Unused renderer hook key.
            _column: Unused renderer hook column.

        Returns:
            Newline-joined default action summary.

        """
        actions = []
        for action in obj.data["DefaultActions"]:
            if action["Type"] == "forward":
                tg = TargetGroup.objects.get(action["TargetGroupArn"])
                actions.append(f"forward:{tg.name}")
            elif action["Type"] == "redirect":
                c = action["RedirectConfig"]
                action_string = "redirect[{}]:".format(
                    "301" if c["StatusCode"] == "HTTP_301" else "302"
                )
                action_string += "{}://{}".format(c["Protocol"].lower(), c["Host"])
                if c.get("Port"):
                    action_string += ":{}".format(c["Port"])
                action_string += "/"
                if c.get("Query"):
                    action_string += "?{}".format(c["Query"])
                actions.append(action_string)
            elif action["Type"] == "fixed":
                c = action["FixedResponseConfig"]
                actions.append(
                    "fixed[{}]: {}".format(c["StatusCode"], c["ContentType"])
                )
        return "\n".join(actions)

    def render_certificates_value(
        self,
        obj: LoadBalancerListener,
        _key: str,
        _column: dict[str, str] | str,
    ) -> str:
        """
        Render listener certificates.

        Args:
            obj: Listener being rendered.
            _key: Unused renderer hook key.
            _column: Unused renderer hook column.

        Returns:
            Newline-joined certificate summary.

        """
        certs = []
        if "Certificates" in obj.data:
            for cert in obj.data["Certificates"]:
                arn = cert["CertificateArn"]
                arn_source = click.style(arn.split(":")[2].upper(), fg="yellow")
                arn_id = arn.rsplit("/")[1]
                arn_string = f"{arn_source}: {arn_id}"
                if cert.get("IsDefault"):
                    certs.append(f"[Default] {arn_string}")
                else:
                    certs.append(arn_string)
        return "\n".join(certs)

    def render_rules_value(
        self,
        obj: LoadBalancerListener,
        _key: str,
        _column: dict[str, str] | str,
    ) -> str:
        """
        Render count of non-default rules.

        Args:
            obj: Listener being rendered.
            _key: Unused renderer hook key.
            _column: Unused renderer hook column.

        Returns:
            Count of non-default rules as a string.

        """
        return str(len(obj.rules))
