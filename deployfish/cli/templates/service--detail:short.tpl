{% from 'macros/service.tpl' import load_balancer %}
{% filter color(fg='green') %}Service: {% endfilter %}{{ obj.name|color(fg='cyan', bold=True) }}
  pk                  :     {{ obj.pk }}
  arn                 :     {{ obj.arn }}
  status              :     {{ obj.data['status'] }}
  cluster             :     {{ obj.data['cluster'] }}
  launch type         :     {{ obj.data['launchType'] }}
{% if obj.data['launchType'] == 'FARGATE' -%}
  platform version    :     {{ obj.data['platformVersion'] }}
{% endif -%}
{%- if obj.data['runningCount'] != 'UNKNOWN' -%}
{% filter color(fg='cyan') %}  task counts{% endfilter %}
    desired           :     {{ obj.data['desiredCount'] }}
    {% filter color(fg='green') %}running{% endfilter %}           :     {{ obj.data['runningCount']|color(fg='green') }}
    {% filter color(fg='yellow') %}pending{% endfilter %}           :     {{ obj.data['pendingCount']|color(fg='yellow') }}
{%- else -%}
  count               :      {{ obj.data['desiredCount'] }}
{%- endif -%}
{%- if obj.data['loadBalancers'] %}
{%- for lb in obj.load_balancers %}{{ load_balancer(lb)|indent(width=2) }}{% endfor -%}
{%- endif %}
