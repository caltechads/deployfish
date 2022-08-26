from datetime import datetime
from typing import Dict, Any

import click
from cement.utils.misc import minimal_logger
from cement.core.output import OutputHandler
from cement.ext.ext_jinja2 import Jinja2TemplateHandler, Jinja2OutputHandler

from deployfish.renderers import TableRenderer, TargetGroupTableRenderer, LBListenerTableRenderer
from deployfish.core.models import TargetGroup

LOG = minimal_logger(__name__)


def color(value: str, **kwargs) -> str:
    """
    Render the string with click.style().
    """
    return click.style(str(value), **kwargs)


def section_title(value: str, **kwargs) -> str:
    """
    Render a section title from ``value``.  This looks like:

        value
        -----

    with optional click font manipulation for ``value``.
    """
    if 'fg' not in kwargs:
        kwargs['fg'] = 'cyan'
    lines = []
    lines.append(click.style(str(value), **kwargs))
    lines.append(click.style('-' * len(value), **kwargs))
    return '\n'.join(lines)


def fromtimestamp(data: float, **_) -> str:
    """
    Convert a unix epoch timestamp to a datetime in our local timezone.
    """
    try:
        return datetime.fromtimestamp(data).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        # This is an AWS timestamp with microseconds
        return datetime.fromtimestamp(data / 1000.0).strftime('%Y-%m-%d %H:%M:%S')


def tabular(data: Dict[str, Any], **kwargs) -> str:
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

    :param columns: a dict that determines the structure of the table
    :param datetime_format Union[str, None]: if specified, use this to render any `datetime.datetime` objects we get
    :param date_format Union[str, None]: if specified, use this to render any `datetime.date` objects we get
    :param float_precision Union[int, None]: if specified, use this to determine the decimal precision
                                             of any `float` objects we get
    """
    renderer_kwargs: Dict[str, Any] = {}
    columns: Dict[str, Any] = {}
    for k, v in list(kwargs.items()):
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

    renderer = TableRenderer(columns, **renderer_kwargs)
    return renderer.render(data)


def target_group_table(data: Dict[str, Any]) -> str:
    """
    Render a table for a list of TargetGroups.
    """
    columns = {
        'Name': 'name',
        'LB Port': 'listener_port',
        'Rules': 'rules',
        'Target Port': 'container_port',
        'Targets': 'targets'
    }
    renderer = TargetGroupTableRenderer(columns)
    return renderer.render(data)


def lb_listener_table(data: Dict[str, Any]) -> str:
    """
    Render a table for a list of elbv2 Listeners.
    """
    columns = {
        'Port': 'port',
        'Protocol': 'protocol',
        'Default Actions': 'default_action',
        '# Rules': 'rules',
        'Certificates': 'certificates',
    }
    renderer = LBListenerTableRenderer(columns)
    return renderer.render(data)


def target_group_listener_rules(obj: TargetGroup) -> str:
    """
    Given a ``TargetGroup`` iterate through its list of LoadBalancerListenerRule objects and return a human readable
    description of those rules.

    :param obj TargetGroup: a TargetGroup object

    :rtype: str
    """
    rules = obj.rules
    conditions = []
    for rule in rules:
        if 'Conditions' in rule.data:
            for condition in rule.data['Conditions']:
                if 'HostHeaderConfig' in condition:
                    for v in condition['HostHeaderConfig']['Values']:
                        conditions.append('hostname:{}'.format(v))
                if 'HttpHeaderConfig' in condition:
                    conditions.append('header:{} -> {}'.format(
                        condition['HttpHeaderConfig']['HttpHeaderName'],
                        ','.join(condition['HttpHeaderConfig']['Values'])
                    ))
                if 'PathPatternConfig' in condition:
                    for v in condition['PathPatternConfig']['Values']:
                        conditions.append('path:{}'.format(v))
                if 'QueryStringConfig' in condition:
                    for v in condition['QueryStringConfig']['Values']:
                        conditions.append('qs:{}={} -> '.format(v['Key'], v['Value']))
                if 'SourceIpConfig' in condition:
                    for v in condition['SourceIpConfig']['Values']:
                        conditions.append('ip:{} -> '.format(v))
                if 'HttpRequestMethod' in condition:
                    for v in condition['HttpRequestMethod']['Values']:
                        conditions.append('verb:{} -> '.format(v))
    if not conditions:
        conditions.append('forward:{}:{}:{} -> CONTAINER:{}:{}'.format(
            obj.load_balancers[0].lb_type,
            obj.listeners[0].port,
            obj.listeners[0].protocol,
            obj.port,
            obj.protocol
        ))
    return '\n'.join(sorted(conditions))


class DeployfishJinja2OutputHandler(Jinja2OutputHandler):
    """
    We're subclassing the cement Jinja2OutputHandler here so we can use our own
    jinja2 template handler instead of the cement default one.
    """

    class Meta:
        label = 'df_jinja2'

    def _setup(self, app):
        OutputHandler._setup(self, app)  # pylint: disable=protected-access
        self.templater = self.app.handler.resolve('template', 'df_jinja2',
                                                  setup=True)


class DeployfishJinja2TemplateHandler(Jinja2TemplateHandler):
    """
    We're subclassing the cement Jinja2TemplateHandler here so we can add some
    custom filters.
    """

    class Meta:
        label = 'df_jinja2'

    def load(self, *args, **kwargs):
        content, _type, _path = super().load(*args, **kwargs)
        self.env.filters['color'] = color
        self.env.filters['section_title'] = section_title
        self.env.filters['fromtimestamp'] = fromtimestamp
        self.env.filters['lb_listener_table'] = lb_listener_table
        self.env.filters['target_group_table'] = target_group_table
        self.env.filters['target_group_listener_rules'] = target_group_listener_rules
        self.env.filters['tabular'] = tabular
        return content, _type, _path


def load(app):
    app.handler.register(DeployfishJinja2OutputHandler)
    app.handler.register(DeployfishJinja2TemplateHandler)
