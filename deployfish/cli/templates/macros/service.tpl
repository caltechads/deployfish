{#
============================================================================================
Service related macros
============================================================================================
#}

{% from 'macros/utils.tpl' import subobject %}

{% macro load_balancer(lb_data) %}
{%- if 'targetGroupArn' in lb_data %}{% set lb_type='ALB' %}{% else %}{% set lb_type='Classic (ELB)' %}{% endif %}
{{ subobject('Load Balancer', lb_type) }}{% if 'targetGroupArn' in lb_data %}
    target group arn:     {{ lb_data['targetGroupArn'] }}
{%- else %}
    name            :     {{ lb_data['loadBalancerName'] }}
{%- endif %}
    container name  :     {{ lb_data['containerName'] }}
    container port  :     {{ lb_data['containerPort'] -}}
{% endmacro %}
