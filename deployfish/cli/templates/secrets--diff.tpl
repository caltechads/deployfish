{% if '$insert' in obj -%}
{% filter color(fg='green', bold=True) %}These secrets would be created in AWS:{% endfilter %}
{% for secret, changes in obj['$insert'].items() %}
  {{ secret|color(fg='yellow') }}: {{changes['Value']}} {% if changes['Type'] == 'SecureString' -%}{% filter color(fg='cyan') %}[SECURE:{{changes['KeyId']}}]{% endfilter %}{% endif %}
{%- endfor %}
{%- endif %}
{% if '$delete' in obj %}

{% filter color(fg='red', bold=True) %}These secrets would be removed from AWS:{% endfilter %}
{% for secret in obj['$delete'] %}
  {{ secret|color(fg='yellow') }}
{%- endfor %}
{%- endif %}
{% if '$update' in obj %}

{% filter color(fg='cyan', bold=True) %}These secrets would be updated in AWS:{% endfilter %}
{% for secret, changes in obj['$update'].items() %}
  {{ secret|color(fg='yellow') }}:
{%- if 'Value' in changes['$update'] %}
    Value -> {{ changes['$update']['Value'] }}
{%- endif -%}
{%- if 'Type' in changes['$update'] -%}
  {%- if changes['$update']['Type'] == 'SecureString' %}
    Secure -> True
    KMS Key ID -> {{ changes['$insert']['KeyId'] }}
  {%- else %}
    Secure -> False
  {%- endif -%}
{%- endif %}
{% endfor %}
{%- endif %}
