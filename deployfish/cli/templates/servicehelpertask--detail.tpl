{% filter color(fg='green') %}Command: {% endfilter %}{{ obj.command|color(fg='cyan', bold=True) }}
  pk                  :     {{ obj.pk }}
  service             :     {{ obj.data['service'] }}
  cluster             :     {{ obj.data['cluster'] }}
  launch type         :     {{ obj.data['launchType'] }}
{%- if obj.data['launchType'] == 'FARGATE' %}
  platform version    :     {{ obj.data['platformVersion'] }}
{% endif -%}
  count               :      {{ obj.data['desiredCount'] }}
