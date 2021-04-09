{% include 'service--detail:short.tpl' %}
{%- if obj.deployments %}

{% filter section_title(fg='cyan', bold=True) %}Deployments{% endfilter %}

{{ obj.deployments|tabular(Status='status', Task_Definition='taskDefinition', Desired='desiredCount', Pending='pendingCount', Running='runningCount', ordering='-Status') }}
{% endif -%}
{%- if obj.events %}

{% filter section_title(fg='cyan', bold=True) %}Events{% endfilter %}

{{ obj.events[:10]|tabular(Timestamp='createdAt', Message='message') }}
{% endif -%}
