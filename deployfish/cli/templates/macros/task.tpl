{#
============================================================================================
Macros related to rendering Tasks
============================================================================================
#}
{% from 'macros/utils.tpl' import subsection %}

{# Render the awsvpcConfiguration a task #}
{# ------------------------------------- #}
{% macro vpc_configuration(obj) -%}
{%- if 'subnets' in obj.vpc_configuration %}
vpc             :     {{ obj.vpc_configuration['vpc'].name}}
subnets
{% for subnet in obj.vpc_configuration['subnets'] %}    {{ subnet.name|color(fg='green') }} [{{ subnet.pk }}] {{ subnet.cidr_block|color(fg='cyan') }}
{% endfor -%}
{% endif -%}{% if 'security_groups' in obj.vpc_configuration %}security_groups
{% for sg in obj.vpc_configuration['security_groups'] %}    {{sg.name|color(fg='green')}} [{{sg.pk}}]
{% endfor -%}
{% endif -%}
allow public IP  :    {{ obj.vpc_configuration['allow_public_ip'] }}
{% endmacro -%}
