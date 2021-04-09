import datetime
from six import string_types
from textwrap import wrap

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

    def __init__(self, columns, datetime_format=None, date_format=None, float_precision=None, ordering=None):
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

        If the value has double underscores in it, e.g. "software__machine_name", this instructs TableRenderer to look
        at an attribute/key on a sub-object. In this case, at the `machine_name` attribute/key of the `software` object
        on our main object.

        :param columns dict(str, str): a dict that determines the structure of the table
        :param datetime_format Union[str, None]: if specified, use this to render any `datetime.datetime` objects we get
        :param date_format Union[str, None]: if specified, use this to render any `datetime.date` objects we get
        :param float_precision Union[int, None]: if specified, use this to determine the decimal precision
                                                 of any `float` objects we get

        """
        assert isinstance(columns, dict), 'TableRenderer: `columns` parameter to __init__ should be a dict'

        self.columns = list(columns.values())
        self.headers = list(columns.keys())
        self.datetime_format = datetime_format if datetime_format else self.DEFAULT_DATETIME_FORMAT
        self.date_format = date_format if date_format else self.DEFAULT_DATE_FORMAT
        self.float_precision = float_precision if float_precision else self.DEFAULT_FLOAT_PRECISION
        self.float_format = '{{:.{}f}}'.format(self.float_precision)
        self.ordering = ordering

    def get_value(self, obj, column):
        try:
            return getattr(obj, column)
        except AttributeError:
            try:
                return obj.render_for_display()[column]
            except KeyError:
                pass
            except AttributeError:
                # This is not a Model object, probably just a bare dict because it doesn't have the
                # .render_for_display() method
                try:
                    return obj[column]
                except KeyError:
                    pass
        raise RenderException(
            '{our_name}: {object_class}.render_for_display() has no key called "{key}", nor does the attribute {object_class}.{key} exist'.format(  # noqa:E501
                our_name=self.__class__.__name__,
                object_class=obj.__class__.__name__,
                key=column
            )
        )

    def render_column(self, obj, column):
        """
        Return the value to put in the table for the attribute named `column` on `obj`, a data object.

        Normally this just does `getattr(obj, column)`, but there are special cases:

            * If the value is a `datetime.datetime`, render it with `.stftime(self.datetime_format)`
            * If the value is a `datetime.date`, render it with `.stftime(self.date_format)`
            * If the value is a `float`, render it with precision
            * If there we have method named `render_{column}_value`, execute that and return its value.

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
                return obj   # the last one should be the value we're looking for
            else:
                value = self.get_value(obj, column)
                if isinstance(value, datetime.datetime):
                    value = value.strftime(self.datetime_format)
                elif isinstance(value, datetime.date):
                    value = value.strftime(self.date_format)
                elif isinstance(value, float):
                    value = self.float_format.format(value)
                else:
                    value = str(value)
        return value

    def render(self, data):
        table = []
        for obj in data:
            row = []
            for column in self.columns:
                value = self.render_column(obj, column)
                if len(value) > 72:
                    value = '\n'.join(wrap(value, 72))
                row.append(value)
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

        return tabulate(table, headers=self.headers)
