{% from 'macros/task-definition.tpl' import task_definition -%}
{% from 'macros/secrets.tpl' import secrets_table -%}
{% from 'macros/task.tpl' import vpc_configuration -%}
{% filter color(fg='green') %}Command: {% endfilter %}{{ obj.command|color(fg='cyan', bold=True) }}
  pk                  :     {{ obj.pk }}
  service             :     {{ obj.data['service'] }}
  cluster             :     {{ obj.data['cluster'] }}
  launch type         :     {{ obj.data['launchType'] }}
{%- if obj.data['launchType'] == 'FARGATE' %}
  platform version    :     {{ obj.data['platformVersion'] }}
{%- endif %}
  count               :     {{ obj.data.get('desiredCount', 1) }}
{% if 'networkConfiguration' in obj.data and obj.task_definition.data.get('networkMode', 'bridge') == 'awsvpc' -%}
{{ vpc_configuration(obj)|indent(width=2) -}}
{% endif -%}
{%- if obj.schedule %}
  {% filter color(fg='yellow', bold=True) %}schedule{% endfilter %}            :     {{ obj.schedule.data['ScheduleExpression']|color(fg='yellow', bold=True) }}
{%- endif %}

{% filter section_title(fg='cyan', bold=True) %}Task Definition{% endfilter %}
{{ task_definition(obj.task_definition)|indent }}
{%- if 'secrets' in includes and obj.secrets %}
{% filter section_title(fg='cyan', bold=True) %}Secrets{% endfilter %}
{{ secrets_table(obj.secrets.values()) }}
{% endif -%}
