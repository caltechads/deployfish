{% filter color(fg='green') %}Cluster: {% endfilter %}{{ obj.name|color(fg='cyan', bold=True) }}
  pk                  :     {{ obj.pk }}
  name                :     {{ obj.name }}
  arn                 :     {{ obj.arn }}
  status              :     {{ obj.data['status'] }}
  instances           :     {{ obj.data['registeredContainerInstancesCount'] }}
{%- if obj.autoscaling_group %}
  autoscaling_group   :     {{ obj.autoscaling_group.name }}
{% endif -%}
{%- if obj.data['settings'] -%}
{% filter color(fg='cyan') %}  settings{% endfilter %}
{% for setting in obj.data['settings'] -%}
    {{ setting['name'] }}: {{ setting['value'] }}
{%- endfor -%}
{% endif -%}
{%- if obj.tags -%}
{% filter color(fg='cyan') %}  tags{% endfilter %}
{% for key, value in obj.tags.items() %}    {{ key|color(fg='yellow') }}: {{ value }}
{% endfor -%}
{% endif -%}
{% filter color(fg='cyan') %}  task counts{% endfilter %}
    {% filter color(fg='green') %}running{% endfilter %}           :     {{ obj.data['runningTasksCount']|color(fg='green') }}
    {% filter color(fg='yellow') %}pending{% endfilter %}           :     {{ obj.data['pendingTasksCount']|color(fg='yellow') }}

{% filter section_title(fg='cyan', bold=True) %}Container instances{% endfilter %}

{{ obj.container_instances|tabular(Name='ec2_instance__tags__Name', Instance_Type='ec2_instance__InstanceType', IP_Address='ec2_instance__PrivateIpAddress', Free_CPU='free_cpu', Free_Memory='free_memory', ordering='Name') }}

{% filter section_title(fg='cyan', bold=True) %}Services{% endfilter %}

{{ obj.services|tabular(Name='name', Version='version', Desired='desiredCount', Running='runningCount', Created='createdAt', ordering='Name') }}
