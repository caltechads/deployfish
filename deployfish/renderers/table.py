from copy import deepcopy
import datetime
from textwrap import wrap
from typing import Dict, Any, List, Optional, Union, cast

import click
from tabulate import tabulate

from deployfish.exceptions import RenderException

from deployfish.core.models import TargetGroup, LoadBalancerListener
from .abstract import AbstractRenderer
from .misc import target_group_listener_rules


# ========================
# Renderers
# ========================

class TableRenderer(AbstractRenderer):
    """
    Render a list of results as an ASCII table.
    """

    DEFAULT_DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    DEFAULT_DATE_FORMAT: str = "%Y-%m-%d"
    DEFAULT_FLOAT_PRECISION: int = 2

    def __init__(
        self,
        columns: Dict[str, Any],
        datetime_format: str = None,
        date_format: str = None,
        float_precision: int = None,
        ordering: str = None,
        tablefmt: str = 'simple',
        show_headers: bool = True
    ):
        """
        `columns` is a dict that determines the structure of the table, like so:

            {
                'ID': 'id',
                'Machine Name': 'machine_name',
                'Name': 'name',
            }

        The keys of `columns` will be used as the column header in the table, and the values in `columns`
        are the names of the attributes on our result objects that contain the data we want to render for that
        column.

        If the value has double underscores in it, e.g. "software__machine_name", this instructs ``TableRenderer`` to
        look at an attribute/key on a sub-object. In this case, at the `machine_name` attribute/key of the `software`
        object on our main object.

        You can configure per column configuration by setting the value of the column to a dict, like so::

            {
                'Timestamp': {
                    'key': 'lastThingTimestamp',
                    'default': '',
                    'datatype': 'timestamp'
                }
            }

        In this dict, ``key`` is the name of the attributes/keys we'll look for in the objects we want to render.  Other
        options::

            * ``default``:  If the attribute/key is not present in our object, return the default value instead of
                            raising an exception.
            * ``datatype``:  Cast the value of this column to this datatype.  See "Manually specified datatypes", below.
            * ``wrap``: Wrap the value to the specified number of columns
            * ``length``: Just render the length of the value.  Useful for counting sub-objects


        Automatcially detected data types:

            * ``datetime.datetime``: render with .strftime() using the format given by either the ``datetime_format``
              kwarg or (if not provided) self.DEFAULT_DATETIME_FORMAT
            * ``datetime.date``: render with .strftime() using the format given by either the ``date_format``
              kwarg or (if not provided) self.DEFAULT_DATE_FORMAT
            * ``float``: render with decimal precision from either the ``float_precision`` kwarg or (if not provided)
              self.DEFAULT_FLOAT_PRECISION
            * ``str``: render as is

            Available datatypes: ``timestamp``, which
            converts an Unix epoch timestamp (seconds or milliseco
                            raising an exception.

        Manually specified data types:

            These get specifed via the `datatype` kwarg on the column definition.

            * ``timestamp``: the raw value is seconds or milliseconds since midnight Jan 1, 1970 UTC.  Convert to a
              ``datetime.datetime`` and render with the rules from ``datetime.datetime``, above
            * ``bytes``: the raw value is number of bytes.  Render in a human readable form (KiB, MB, GiB, etc.)


        :param columns dict(str, str): a dict that determines the structure of the table
        :param datetime_format Union[str, None]: if specified, use this to render any `datetime.datetime` objects we get
        :param date_format Union[str, None]: if specified, use this to render any `datetime.date` objects we get
        :param float_precision Union[int, None]: if specified, use this to determine the decimal precision
                                                 of any `float` objects we get
        :param tablefmt str: provide this to tabulate() to determine the table format

        """
        super().__init__()
        assert isinstance(columns, dict), 'TableRenderer: `columns` parameter to __init__ should be a dict'

        self.columns: List[str] = list(columns.values())
        self.headers: List[str] = list(columns.keys())
        self.datetime_format: str = datetime_format if datetime_format else self.DEFAULT_DATETIME_FORMAT
        self.date_format: str = date_format if date_format else self.DEFAULT_DATE_FORMAT
        self.float_precision: int = float_precision if float_precision else self.DEFAULT_FLOAT_PRECISION
        self.float_format: str = '{{:.{}f}}'.format(self.float_precision)
        self.ordering: Optional[str] = ordering
        self.tablefmt: str = tablefmt
        self.show_headers: bool = show_headers

    def get_value(self, obj: Any, column: Union[Dict[str, str], str]) -> Any:
        if isinstance(column, dict):
            data_key = column['key']
        else:
            data_key = column
        try:
            return getattr(obj, data_key)
        except AttributeError:
            try:
                return obj.render_for_display()[data_key]
            except KeyError:
                pass
            except AttributeError:
                # This is not a Model object, probably just a bare dict because it doesn't have the
                # .render_for_display() method
                try:
                    return obj[data_key]
                except KeyError:
                    pass
        if isinstance(column, dict):
            if 'default' in column:
                return column['default']

        # This is for debugging our templates.  We should never get here in production.
        from pprint import pprint
        if isinstance(obj, dict):
            pprint(obj)
        else:
            print('dir(obj):\n')
            pprint(dir(obj))
            print('\nobj.render_for_display():\n')
            pprint(obj.render_for_display())
        raise RenderException(
            click.style(
                '\n\n{our_name}: Could not dereference "{key}"'.format(our_name=self.__class__.__name__, key=data_key),
                fg='red'
            )
        )

    def human_bytes(self, value: Union[float, int], suffix: str = 'B') -> str:
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(value) < 1024.0:
                return "%3.1f%s%s" % (value, unit, suffix)
            value /= 1024.0
        return "%.1f%s%s" % (value, 'Yi', suffix)

    def _default_cast(self, value: Any) -> str:
        if isinstance(value, datetime.datetime):
            value = value.strftime(self.datetime_format)
        elif isinstance(value, datetime.date):
            value = value.strftime(self.date_format)
        elif isinstance(value, float):
            value = self.float_format.format(value)
        return value

    def cast_column(self, obj: Any, value: Any, column: Union[Dict[str, str], str]) -> str:
        """
        Try to reformat a value into a more human friendly form:

            * If the value is a `datetime.datetime`, render it with `.stftime(self.datetime_format)`
            * If the value is a `datetime.date`, render it with `.stftime(self.date_format)`
            * If the value is a `float`, render it with precision

        """
        if value == '':
            return value
        if isinstance(column, dict):
            if 'length' in column:
                return str(len(value))
            if 'datatype' not in column:
                value = self._default_cast(value)
            else:
                if column['datatype'] == 'timestamp':
                    value = int(value)
                    try:
                        value = datetime.datetime.fromtimestamp(value).strftime(self.datetime_format)
                    except ValueError:
                        # This is an AWS timestamp in milliseconds, not seconds
                        value = datetime.datetime.fromtimestamp(value / 1000.0).strftime(self.datetime_format)
                    value = self._default_cast(value)
                elif column['datatype'] == 'bytes':
                    value = int(value)
                    value = self.human_bytes(value)
            if 'wrap' in column:
                value = str(value)
                value = '\n'.join(wrap(value, cast(int, column['wrap'])))
        return value

    def render_column(self, obj: Any, column: Union[Dict[str, str], str]) -> str:
        """
        Return the value to put in the table for the attribute named `column` on `obj`, a data object.

        Normally this tries returns the value either through `getattr(obj, column)` or through
        ``obj.render_for_display()[column]``.  However, if there we have method named `render_{column}_value`, execute
        that instead and return its value.

        :param obj: the data object
        :param column str: the attribute to access on the `obj`

        :rtype: str
        """

        if isinstance(column, dict):
            key = column['key']
        else:
            key = column
        if hasattr(self, f'render_{column}_value'):
            value = getattr(self, f'render_{column}_value')(obj, key, column)
        else:
            if '__' in key:
                refs = key.split('__')
                ref: Optional[str] = refs.pop(0)
                while ref:
                    if isinstance(column, dict):
                        sub_column = cast(Dict[str, Any], deepcopy(column))
                        sub_column['key'] = ref
                        obj = self.get_value(obj, sub_column)
                    else:
                        obj = self.get_value(obj, ref)
                    try:
                        ref = refs.pop(0)
                    except IndexError:
                        ref = None
                value = obj  # the last one should be the value we're looking for
                value = self.cast_column(obj, value, column)
                return value
            value = self.get_value(obj, column)
            value = self.cast_column(obj, value, column)
        return value

    def render(self, data: Any, **_) -> str:
        data = cast(List[Any], data)
        table = []
        for obj in data:
            row = []
            for column in self.columns:
                row.append(self.render_column(obj, column))
            table.append(row)
        if self.ordering:
            reverse = False
            order_column = self.ordering
            if order_column.startswith('-'):
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

    def render_load_balancers_value(self, obj: TargetGroup, key: str, column: Union[Dict[str, str], str]) -> str:
        load_balancer_names = [lb.name for lb in obj.load_balancers]
        return '\n'.join(load_balancer_names)

    def render_targets_value(self, obj: TargetGroup, key: str, column: Union[Dict[str, str], str]) -> str:
        target_names = [t.target.name for t in obj.targets]
        return '\n'.join(target_names)

    def render_rules_value(self, obj: TargetGroup, key: str, column: Union[Dict[str, str], str]) -> str:
        return target_group_listener_rules(obj)

    def render_listener_port_value(self, obj: TargetGroup, key: str, column: Union[Dict[str, str], str]) -> str:
        return '\n'.join(["{}:{}".format(l.protocol, str(l.port)) for l in obj.listeners])

    def render_container_port_value(self, obj: TargetGroup, key: str, column: Union[Dict[str, str], str]) -> str:
        return "{}:{}".format(obj.data['Protocol'], obj.data['Port'])


class LBListenerTableRenderer(TableRenderer):

    def render_default_action_value(
        self,
        obj: LoadBalancerListener,
        key: str,
        column: Union[Dict[str, str], str]
    ) -> str:
        actions = []
        for action in obj.data['DefaultActions']:
            if action['Type'] == 'forward':
                tg = TargetGroup.objects.get(action['TargetGroupArn'])
                actions.append('forward:{}'.format(tg.name))
            elif action['Type'] == 'redirect':
                c = action['RedirectConfig']
                action_string = 'redirect[{}]:'.format(
                    '301' if c['StatusCode'] == 'HTTP_301' else '302'
                )
                action_string += "{}://{}".format(c['Protocol'].lower(), c['Host'])
                if 'Port' in c and c['Port']:
                    action_string += ":{}".format(c['Port'])
                action_string += '/'
                if 'Query' in c and c['Query']:
                    action_string += '?{}'.format(c['Query'])
                actions.append(action_string)
            elif action['Type'] == 'fixed':
                c = action['FixedResponseConfig']
                actions.append('fixed[{}]: {}'.format(c['StatusCode'], c['ContentType']))
        return '\n'.join(actions)

    def render_certificates_value(self, obj: LoadBalancerListener, key: str, column: Union[Dict[str, str], str]) -> str:
        certs = []
        if 'Certificates' in obj.data:
            for cert in obj.data['Certificates']:
                arn = cert['CertificateArn']
                arn_source = click.style(arn.split(':')[2].upper(), fg='yellow')
                arn_id = arn.rsplit('/')[1]
                arn_string = '{}: {}'.format(arn_source, arn_id)
                if 'IsDefault' in cert and cert['IsDefault']:
                    certs.append('[Default] {}'.format(arn_string))
                else:
                    certs.append(arn_string)
        return '\n'.join(certs)

    def render_rules_value(self, obj: LoadBalancerListener, key: str, column: Union[Dict[str, str], str]) -> str:
        return str(len(obj.rules))
