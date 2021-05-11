{% from 'macros/utils.tpl' import heading, subsection, subobject, tags -%}
{{ subobject('Application Load Balancer (ELB)', obj.name) }}
  pk                  :     {{ obj.pk }}
  arn                 :     {{ obj.arn }}
  name                :     {{ obj.name }}
  scheme              :     {{ obj.scheme }}
  state                :    {{ obj.data['State']['Name'] }}
  hostname            :     {{ obj.hostname }}
  created             :     {{ obj.data['CreatedTime'].strftime('%Y-%m-%d %H:%M:%S') }}
{%- if obj.ssl_certificate_arn %}
  ssl certificate     :     {{ obj.ssl_certificate_arn }}
  ssl policy          :     {{ obj.ssl_policy }}
{%- endif %}

  {{ subsection('networking') }}
    VPC               :     {{ obj.data['VpcId'] }}
    subnets           :     {{ obj.data['AvailabilityZones']|map(attribute='SubnetId')|join(', ') }}
    availability zones:     {{ obj.data['AvailabilityZones']|map(attribute='ZoneName')|join(', ') }}
    security groups   :     {{ obj.data['SecurityGroups']|join(', ') }}

{{ heading('Listeners') }}

{{ obj.listeners|alb_listener_table }}

{{ heading('Target Groups') }}

{{ obj.target_groups|target_group_table }}
