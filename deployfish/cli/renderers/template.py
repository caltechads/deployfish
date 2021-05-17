from deployfish import jinja_env

from .filters import (
    color,
    fromtimestamp,
    section_title,
    tabular,
    target_group_table,
    alb_listener_table,
)
from .misc import target_group_listener_rules

from .abstract import AbstractRenderer

jinja_env.filters['color'] = color
jinja_env.filters['tabular'] = tabular
jinja_env.filters['target_group_table'] = target_group_table
jinja_env.filters['alb_listener_table'] = alb_listener_table
jinja_env.filters['target_group_listener_rules'] = target_group_listener_rules
jinja_env.filters['section_title'] = section_title
jinja_env.filters['fromtimestamp'] = fromtimestamp


# ========================
# Renderers
# ========================

class TemplateRenderer(AbstractRenderer):
    """
    Given a template path, render an object with that template.
    """

    template_file = None

    def render(self, data, style=None, template=None, context=None):
        if context is None:
            context = {}
        if not template:
            template = self.template_file
        if not style:
            style = ''
        else:
            style = ':{}'.format(style)
        operation = 'info'
        if isinstance(data, list) or isinstance(data, tuple):
            name = data[0].__class__.__name__.lower()
            operation = 'list'
        else:
            name = data.__class__.__name__.lower()
            operation = 'detail'
        if not template:
            template_file = '{}--{}{}.tpl'.format(name, operation, style)
        else:
            template_file = template
        context['obj'] = data
        template = jinja_env.get_template(template_file)
        return template.render(**context)
