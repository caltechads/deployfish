{% filter color(fg='green') %}Cloudwatch Log Stream: {% endfilter %}{{ obj.name|color(fg='cyan', bold=True) }}
  pk                  :     {{ obj.pk }}
  arn                 :     {{ obj.arn }}
  log group           :     {{ obj.data['logGroupName'] }}
  created             :     {{ obj.data['creationTime']|fromtimestamp }}
{%- if 'firstEventTimestamp' in obj.data %}
  first event         :     {{ obj.data['firstEventTimestamp']|fromtimestamp }}
{%- endif %}
{%- if 'lastEventTimestamp' in obj.data %}
  last event          :     {{ obj.data['lastEventTimestamp']|fromtimestamp }}
{%- endif %}
{%- if 'lastIngetstionTime' in obj.data %}
  last event          :     {{ obj.data['lastIngestionTime']|fromtimestamp }}
{%- endif %}

{% filter section_title(fg='cyan', bold=True) %}Events{% endfilter %}
{% set paginator = obj.events(sleep=0) %}
{% for page in paginator -%}
{% for event in page -%}
{{ event['timestamp']|color(fg='cyan') }}   {{ event['message'] }}
{% endfor %}
{% endfor %}
