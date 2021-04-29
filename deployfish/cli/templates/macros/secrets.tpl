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
