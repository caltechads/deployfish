{#
============================================================================================
Service related macros
============================================================================================
#}

{% from 'macros/utils.tpl' import subobject, subsection %}
{% from 'macros/target-group.tpl' import tg_health_check %}
{% from 'macros/classicloadbalancer.tpl' import elb_health_check %}

{% macro load_balancer(lb_data) %}
{%- if 'targetGroupArn' in lb_data %}{% set lb_type='ALB' %}{% else %}{% set lb_type='Classic (ELB)' %}{% endif %}
{{ subobject('Load Balancer', lb_type) }}{% if 'targetGroupArn' in lb_data %}
    load balancer   :     {{ lb_data['TargetGroup'].load_balancers[0].name }}
    hostname        :     {{ lb_data['TargetGroup'].load_balancers[0].hostname }}
    target group    :     {{ lb_data['TargetGroup'].name }}
    target group arn:     {{ lb_data['TargetGroup'].arn }}
    {{ subsection('routing rules') }}
      {{ lb_data['TargetGroup']|target_group_listener_rules|indent(width=6) }}
    {{ subsection('health check') }}
    {{- tg_health_check(lb_data['TargetGroup'])|indent|indent(width=2) }}
{%- else %}
    name            :     {{ lb_data['loadBalancerName'] }}
    hostname        :     {{ lb_data['LoadBalancer'].hostname }}
    {{ subsection('health check') }}
    {{- elb_health_check(lb_data['LoadBalancer'])|indent(width=6) }}
{%- endif %}
    container name  :     {{ lb_data['containerName'] }}
    container port  :     {{ lb_data['containerPort'] -}}
{% endmacro %}
