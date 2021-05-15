from datetime import datetime

import click

from .table import ALBListenerTableRenderer, TableRenderer, TargetGroupTableRenderer


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
    renderer_kwargs = {}
    columns = {}
    for k, v in kwargs.items():
        if k in ['ordering', 'date_format', 'datetime_format', 'float_precision', 'tablefmt', 'show_headers']:
            renderer_kwargs[k] = v
        elif k.endswith('_datatype'):
            k = k.replace('_datatype', '')
            k = k.replace('_', ' ')
            if k not in columns:
                columns[k] = {}
            columns[k]['datatype'] = v
        elif k.endswith('_default'):
            k = k.replace('_default', '')
            k = k.replace('_', ' ')
            if k not in columns:
                columns[k] = {}
            columns[k]['default'] = v
        else:
            k = k.replace('_', ' ')
            if k not in columns:
                columns[k] = {}
            columns[k]['key'] = v

    renderer = TableRenderer(columns, *renderer_kwargs)
    return renderer.render(data)


def target_group_table(data):
    """
    Render a table for a list of TargetGroups.
    """
    columns = {
        'Name': 'name',
        'ALB Port': 'listener_port',
        'Rules': 'rules',
        'Target Port': 'container_port',
        'Targets': 'targets'
    }
    renderer = TargetGroupTableRenderer(columns)
    return renderer.render(data)


def alb_listener_table(data):
    """
    Render a table for a list of ALB Listeners.
    """
    columns = {
        'Port': 'port',
        'Protocol': 'protocol',
        'Default Actions': 'default_action',
        '# Rules': 'rules',
        'Certificates': 'certificates',
    }
    renderer = ALBListenerTableRenderer(columns)
    return renderer.render(data)


def fromtimestamp(data, **kwargs):
    """
    Convert a unix epoch timestamp to a datetime in our local timezone.
    """
    try:
        return datetime.fromtimestamp(data).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        # This is an AWS timestamp with microseconds
        return datetime.fromtimestamp(data / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
