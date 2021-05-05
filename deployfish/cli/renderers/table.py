import datetime
from textwrap import wrap

import click
from tabulate import tabulate

from deployfish.exceptions import RenderException

from .abstract import AbstractRenderer


# ========================
# Renderers
# ========================

class TableRenderer(AbstractRenderer):
    """
    Render a list of results as an ASCII table.
    """

    DEFAULT_DATETIME_FORMAT = "%b %d, %Y %I:%M:%S %p"
    DEFAULT_DATE_FORMAT = "%b %d, %Y"
    DEFAULT_FLOAT_PRECISION = 2

    def __init__(self, columns, datetime_format=None, date_format=None, float_precision=None, ordering=None,
                 tablefmt='simple', show_headers=True):
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


        Automatcially detected data types:

            * ``datetime.datetime``: render with .strftime() using the format given by either the ``datetime_format``
              kwarg or (if not provided) self.DEFAULT_DATETIME_FORMAT
            * ``datetime.date``: render with .strftime() using the format given by either the ``date_format``
              kwarg or (if not provided) self.DEFAULT_DATE_FORMAT
            * ``float``: render with decimal precision from either the ``float_precision`` kwarg or (if not provided)
              self.DEFAULT_FLOAT_PRECISION
            * ``str``: render, wrapping at 72 colums

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
        assert isinstance(columns, dict), 'TableRenderer: `columns` parameter to __init__ should be a dict'

        self.columns = list(columns.values())
        self.headers = list(columns.keys())
        self.datetime_format = datetime_format if datetime_format else self.DEFAULT_DATETIME_FORMAT
        self.date_format = date_format if date_format else self.DEFAULT_DATE_FORMAT
        self.float_precision = float_precision if float_precision else self.DEFAULT_FLOAT_PRECISION
        self.float_format = '{{:.{}f}}'.format(self.float_precision)
        self.ordering = ordering
        self.tablefmt = tablefmt
        self.show_headers = show_headers

    def get_value(self, obj, column):
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

        from pprint import pprint
        pprint(obj.render_for_display())
        raise RenderException(
            click.style(
                '\n\n{our_name}: Could not dereference "{key}"'.format(our_name=self.__class__.__name__, key=column),
                fg='red'
            )
        )

    def human_bytes(self, value, suffix='B'):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(value) < 1024.0:
                return "%3.1f%s%s" % (value, unit, suffix)
            value /= 1024.0
        return "%.1f%s%s" % (value, 'Yi', suffix)

    def _default_cast(self, obj, value):
        if isinstance(value, datetime.datetime):
            value = value.strftime(self.datetime_format)
        elif isinstance(value, datetime.date):
            value = value.strftime(self.date_format)
        elif isinstance(value, float):
            value = self.float_format.format(value)
        else:
            value = str(value)
            value = '\n'.join(wrap(value, 72))
        return value

    def cast_column(self, obj, value, column):
        """
        Try to reformat a value into a more human friendly form:

            * If the value is a `datetime.datetime`, render it with `.stftime(self.datetime_format)`
            * If the value is a `datetime.date`, render it with `.stftime(self.date_format)`
            * If the value is a `float`, render it with precision

        """
        if value == '':
            return value
        if isinstance(column, dict):
            if 'datatype' not in column:
                return self._default_cast(obj, value)
            else:
                if column['datatype'] == 'timestamp':
                    value = int(value)
                    try:
                        return datetime.datetime.fromtimestamp(value).strftime(self.datetime_format)
                    except ValueError:
                        # This is an AWS timestamp with microseconds
                        return datetime.datetime.fromtimestamp(value / 1000.0).strftime(self.datetime_format)
                elif column['datatype'] == 'bytes':
                    value = int(value)
                    return self.human_bytes(value)

        if isinstance(value, datetime.datetime):
            value = value.strftime(self.datetime_format)
        elif isinstance(value, datetime.date):
            value = value.strftime(self.date_format)
        elif isinstance(value, float):
            value = self.float_format.format(value)
        else:
            value = str(value)
            value = '\n'.join(wrap(value, 72))
        return value

    def render_column(self, obj, column):
        """
        Return the value to put in the table for the attribute named `column` on `obj`, a data object.

        Normally this tries returns the value either through `getattr(obj, column)` or through
        ``obj.render_for_display()[column]``.  However, if there we have method named `render_{column}_value`, execute
        that instead and return its value.

        :param obj: the data object
        :param column str: the attribute to access on the `obj`

        :rtype: str
        """

        if hasattr(self, f'render_{column}_value'):
            value = getattr(self, f'render_{column}_value')(obj, column)
        else:
            if '__' in column:
                refs = column.split('__')
                ref = refs.pop(0)
                while ref:
                    obj = self.get_value(obj, ref)
                    try:
                        ref = refs.pop(0)
                    except IndexError:
                        ref = None
                value = obj  # the last one should be the value we're looking for
                value = self.cast_column(obj, value, column)
                return value
            else:
                value = self.get_value(obj, column)
                value = self.cast_column(obj, value, column)
        return value

    def render(self, data):
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
        else:
            return tabulate(table, tablefmt=self.tablefmt)
