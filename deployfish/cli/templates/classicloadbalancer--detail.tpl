{% from 'macros/utils.tpl' import heading, subsection, subobject, tags -%}
{{ subobject('Classic Load Balancer (ELB)', obj.name) }}
  pk                  :     {{ obj.pk }}
  name                :     {{ obj.name }}
  scheme              :     {{ obj.scheme }}
  hostname            :     {{ obj.hostname }}
  created             :     {{ obj.data['CreatedTime'].strftime('%Y-%m-%d %H:%M:%S') }}
{%- if obj.ssl_certificate_arn %}
  ssl certificate     :     {{ obj.ssl_certificate_arn }}
  ssl policy          :     {{ obj.ssl_policy }}
{%- endif %}

  {{ subsection('networking') }}
    VPC               :     {{ obj.data['VPCId'] }}
    subnets           :     {{ obj.data['Subnets']|join(', ') }}
    availability zones:     {{ obj.data['AvailabilityZones']|join(', ') }}
    security groups   :     {{ obj.data['SecurityGroups']|join(', ') }}

  {{ subsection('health check') }}
    target            :     {{ obj.data['HealthCheck']['Target'] }}
    interval          :     {{ obj.data['HealthCheck']['Interval'] }}
    timeout           :     {{ obj.data['HealthCheck']['Timeout'] }}
    unhealthy count   :     {{ obj.data['HealthCheck']['UnhealthyThreshold'] }}
    healthy count     :     {{ obj.data['HealthCheck']['HealthyThreshold'] }}

{{ heading('Listeners') }}

{{ obj.listeners|tabular(LB_Protocol='Protocol', LB_Port='LoadBalancerPort', Instance_Protocol='InstanceProtocol', Instance_Port='InstancePort', ordering='LB_Protocol') }}

{{ heading('Targets') }}

{{ obj.targets|tabular(Name='name', State='Instance__State__Name', Health='State', Code='ReasonCode', Description='Description', Instance_Type='Instance__InstanceType', IP_Address='ip_address', ordering='Name') }}
