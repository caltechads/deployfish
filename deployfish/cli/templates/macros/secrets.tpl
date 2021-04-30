{% macro secrets_table(objs) %}
{% set secrets=objs|selectattr("arn") -%}
{% set non_existant_parameters=objs|selectattr("arn", "none") -%}
{{ secrets|tabular(Name='secret_name', Secure='is_secure', Value='value', ordering='Name') }}
{% if non_existant_parameters %}

These secrets referenced by the task definition do not exist in AWS SSM Parameter Store:
{% for s in non_existant_parameters %}
   {{s.pk|color(fg='red')}}
{%- endfor -%}
{% endif -%}
{% endmacro %}

{% macro secrets_list(obj) %}
{%- for name in obj.keys()|sort %}
{% if obj[name].arn -%}
{{ name|color(fg='yellow') }}: {{obj[name].value }} {% if obj[name].kms_key_id -%}{% filter color(fg='cyan') %}[SECURE:{{obj[name].kms_key_id}}]{% endfilter %}{% endif %}
{%- else -%}
{{ name|color(fg='yellow') }}: {% filter color(fg='red') %}NOT IN AWS{% endfilter %}
{%- endif %}
{%- endfor %}
{% endmacro %}
