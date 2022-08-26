{% from 'macros/task-definition.tpl' import task_definition -%}
{% from 'macros/secrets.tpl' import secrets_table -%}
{% from 'macros/task.tpl' import vpc_configuration -%}
{% filter color(fg='green') %}Task: {% endfilter %}{{ obj.name|color(fg='cyan', bold=True) }}
  pk                  :     {{ obj.pk }}
{%- if 'service' in obj.data %}
  service             :     {{ obj.data['service'] }}
{%- endif %}
  cluster             :     {{ obj.data['cluster'] }}
  launch type         :     {{ obj.data['launchType'] }}
{%- if obj.data['launchType'] == 'FARGATE' %}
  platform version    :     {{ obj.data.get('platformVersion', 'LATEST') }}
{%- endif %}
  count               :     {{ obj.data.get('count', 1) }}
{%- if obj.schedule %}
  {% filter color(fg='yellow', bold=True) %}schedule{% endfilter %}            :     {{ obj.schedule.data['ScheduleExpression']|color(fg='yellow', bold=True) }}  {% if not obj.schedule.enabled %}{% filter color(fg='red', bold=True)%}[DISABLED]{% endfilter %}{% endif %}
{%- endif %}
{% if 'networkConfiguration' in obj.data %}{% filter color(fg='cyan') %}  vpc configuration{% endfilter %}{{ vpc_configuration(obj)|indent(width=4)}}{% endif %}

{% filter section_title(fg='cyan', bold=True) %}Task Definition{% endfilter %}
{{ task_definition(obj.task_definition)|indent }}
