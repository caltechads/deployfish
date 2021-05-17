{% from 'macros/utils.tpl' import heading, subsection, subobject, tags -%}
{{ subobject('Cluster', obj.name) }}
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
{{ subsection('  task counts')|indent(width=2) }}
      {% filter color(fg='green') %}running{% endfilter %}           :     {{ obj.data['runningTasksCount']|color(fg='green') }}
      {% filter color(fg='yellow') %}pending{% endfilter %}           :     {{ obj.data['pendingTasksCount']|color(fg='yellow') }}
{%- if obj.tags %}{{ tags(obj.tags)|indent(width=2) }}{% endif %}

{{ heading('Container instances') }}

{{ obj.container_instances|tabular(Name='ec2_instance__tags__Name', Instance_Type='ec2_instance__InstanceType', IP_Address='ec2_instance__PrivateIpAddress', Free_CPU='free_cpu', Free_Memory='free_memory', ordering='Name') }}

{{ heading('Services') }}

{{ obj.services|tabular(Name='name', Version='version', Desired='desiredCount', Running='runningCount', Created='createdAt') }}
