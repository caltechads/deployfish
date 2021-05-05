{% from 'macros/utils.tpl' import subobject -%}
{% from 'macros/task-definition.tpl' import task_definition -%}
{% from 'macros/invoked-task.tpl' import task_container, status, timestamps -%}
{% filter color(fg='green') %}Invoked Task: {% endfilter %}{{ obj.name|color(fg='cyan', bold=True) }}
  pk                  :     {{ obj.pk }}
  cluster             :     {{ obj.data['cluster'] }}
  availability zone   :     {{ obj.data['availabilityZone'] }}
  connectivity        :     {{ obj.data['connectivity'] }}
  launch type         :     {{ obj.data['launchType'] }}
{%- if 'group' in obj.data %}
  group               :     {{ obj.data['group'] }}
{%- endif %}
{%- if 'cpu' in obj.data %}
  cpu                 :     {{ obj.data['cpu'] }}
{%- endif %}
{%- if 'memory' in obj.data %}
  memory              :     {{ obj.data['memory'] }}
{%- endif %}
{{ status(obj)|indent(width=2) }}

{% filter color(fg='cyan') %}  timestamps{% endfilter %}
{{ timestamps(obj)|indent }}
{%- for container in obj.data['containers'] %}
{{ subobject('Container', container['name'])|indent(width=2) }}
{{ task_container(container)|indent(width=4) }}
{%- endfor %}

{% filter section_title(fg='cyan', bold=True) %}Task Definition{% endfilter %}
{{ task_definition(obj.task_definition)|indent }}
