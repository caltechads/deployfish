{% from 'macros/task-definition.tpl' import task_definition -%}
{% from 'macros/secrets.tpl' import secrets_table -%}
{% include 'service--detail:short.tpl' %}

{% filter section_title(fg='cyan', bold=True) %}Task Definition{% endfilter %}
{{ task_definition(obj.task_definition)|indent }}
{% if includes is not defined or ('secrets' in includes and obj.secrets) %}
{% filter section_title(fg='cyan', bold=True) %}Secrets{% endfilter %}
{{ secrets_table(obj.secrets.values()) }}
{% endif -%}
{%- if includes is not defined or ('deployments' in includes and obj.deployments) %}

{% filter section_title(fg='cyan', bold=True) %}Deployments{% endfilter %}

{{ obj.deployments|tabular(Status='status', Task_Definition='taskDefinition', Desired='desiredCount', Pending='pendingCount', Running='runningCount', ordering='-Status') }}
{% endif -%}
{%- if excludes is defined and 'events' not in excludes and obj.events %}

{% filter section_title(fg='cyan', bold=True) %}Events{% endfilter %}

{{ obj.events[:10]|tabular(Timestamp='createdAt', Message='message') }}
{% endif -%}
