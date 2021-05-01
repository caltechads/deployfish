{#
============================================================================================
Macros related to rendering Tasks
============================================================================================
#}
{% from 'macros/utils.tpl' import subsection %}

{# Render the awsvpcConfiguration a task #}
{# ------------------------------------- #}
{% macro vpc_configuration(obj) -%}
{% if 'subnets' in obj.data['networkConfiguration']['awsvpcConfiguration'] %}
subnets             :     {{ obj.data['networkConfiguration']['awsvpcConfiguration']['subnets']|join(', ') }}
{% endif -%}
{% if 'securityGroups' in obj.data['networkConfiguration']['awsvpcConfiguration'] -%}
security groups     :     {{ obj.data['networkConfiguration']['awsvpcConfiguration']['securityGroups']|join(', ') }}
{% endif -%}
{% if 'allowPublicIp' in obj.data['networkConfiguration']['awsvpcConfiguration'] -%}
allow public IP     :     {{ obj.data['networkConfiguration']['awsvpcConfiguration']['allowPublicIp'] }}
{% endif -%}
{% endmacro -%}
