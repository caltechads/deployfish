{% from 'macros/awslogs.tpl' import log_streams_table -%}
{% filter color(fg='green') %}Cloudwatch Log Group: {% endfilter %}{{ obj.name|color(fg='cyan', bold=True) }}
  pk                  :     {{ obj.pk }}
  arn                 :     {{ obj.arn }}
  created             :     {{ obj.data['creationTime']|fromtimestamp }}
  retention days      :     {{ obj.data['retentionInDays']|default('infinite') }}
  size (bytes)        :     {{ obj.data['storedBytes'] }}
{% if 'kmsKeyId' in obj.data -%}
  encrypted           :     True
  kms key id          :     {{ obj.data['kmsKeyId'] }}
{%- endif %}

{% filter section_title(fg='cyan', bold=True) %}25 Most Recent Log Streams{% endfilter %}
{{ log_streams_table(obj, maxitems=25) }}
