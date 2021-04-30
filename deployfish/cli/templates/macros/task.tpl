{#
============================================================================================
Macros related to rendering Tasks
============================================================================================
#}
{% from 'macros/utils.tpl' import subsection %}

{# Render the awsVpcConfiguration a task #}
{# ------------------------------------- #}
{% macro vpc_configuration(obj) -%}
{% if 'subnets' in obj.data['networkConfiguration']['awsVpcConfiguration'] %}
subnets             :     {{ obj.data['networkConfiguration']['awsVpcConfiguration']['subnets']|join(', ') }}
{% endif -%}
{% if 'securityGroups' in obj.data['networkConfiguration']['awsVpcConfiguration'] -%}
security groups     :     {{ obj.data['networkConfiguration']['awsVpcConfiguration']['securityGroups']|join(', ') }}
{% endif -%}
{% if 'allowPublicIp' in obj.data['networkConfiguration']['awsVpcConfiguration'] -%}
allow public IP     :     {{ obj.data['networkConfiguration']['awsVpcConfiguration']['allowPublicIp'] }}
{% endif -%}
{% endmacro -%}
