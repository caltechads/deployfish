{% for task in obj %}
{% filter color(fg='green') %}Command: {% endfilter %}{{ task.command|color(fg='cyan', bold=True) }}
  pk                  :     {{ task.pk }}
  service             :     {{ task.data['service'] }}
  cluster             :     {{ task.data['cluster'] }}
  launch type         :     {{ task.data['launchType'] }}
{%- if task.data['launchType'] == 'FARGATE' %}
  platform version    :     {{ task.data['platformVersion'] }}
{% endif -%}
  count               :      {{ task.data['desiredCount'] }}
{% endfor %}
