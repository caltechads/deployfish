{% filter color(fg='green') %}Service: {% endfilter %}{{ obj.name|color(fg='cyan', bold=True) }}
  pk                  :     {{ obj.pk }}
  name                :     {{ obj.name }}
  cluster             :     {{ obj.data['cluster'] }}
  launch type         :     {{ obj.data['launchType'] }}
{% if obj.data['launchType'] == 'FARGATE' -%}
  platform version    :     {{ obj.data['platformVersion'] }}
{% endif -%}
{%- if obj.data['runningCount'] != 'UNKNOWN' -%}
{% filter color(fg='cyan') %}  task counts{% endfilter %}
    desired           :     {{ obj.data['desiredCount'] }}
    {% filter color(fg='green') %}running{% endfilter %}           :     {{ obj.data['runningCount']|color(fg='green') }}
    {% filter color(fg='yellow') %}pending{% endfilter %}           :     {{ obj.data['desiredCount']|color(fg='yellow') }}
{%- else -%}
  count               :      {{ obj.data['desiredCount'] }}
{%- endif -%}
{%- if obj.data['loadBalancers'] %}
  {% filter color(fg='cyan') %}load balancers{% endfilter %}
  {%- for lb in obj.data['loadBalancers'] -%}
    {%- if lb['targetGroupArn'] %}
   -  target group ARN:     {{ lb['targetGroupArn'] }}
    {%- else %}
   -  load balancer   :     {{ lb['loadBalancerName'] }}
    {%- endif %}
      container name  :     {{ lb['containerName'] }}
      container port  :     {{ lb['containerPort'] }}
  {%- endfor -%}
{%- endif %}
