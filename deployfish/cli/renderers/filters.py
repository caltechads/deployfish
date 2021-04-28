from copy import copy

import click

from .table import TableRenderer


def color(value, **kwargs):
    """
    Render the string with click.style().
    """
    return click.style(str(value), **kwargs)


def section_title(value, **kwargs):
    if 'fg' not in kwargs:
        kwargs['fg'] = 'cyan'
    lines = []
    lines.append(click.style(str(value), **kwargs))
    lines.append(click.style('-' * len(value), **kwargs))
    return '\n'.join(lines)


def tabular(data, **kwargs):
    """
    Render a table.

    `kwargs` determine which columns are displayed, with the kwarg being the title of the column and the value
    being the name of the attribute on the objects to display.  For example::

        {{ obj.services|tabular(Name='name', Version='version', 'Desired': 'desiredCount', 'Running': 'runningCount') }}

    Will display::



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
    kwargs_copy = copy(kwargs)
    columns = {
        k.replace('_', ' '): kwargs_copy.pop(k)
        for k in kwargs.keys()
        if k not in ['ordering', 'date_format', 'datetime_format', 'float_precision', 'tablefmt', 'show_headers']
    }

    renderer = TableRenderer(columns, **kwargs_copy)
    return renderer.render(data)