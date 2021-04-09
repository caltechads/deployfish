{% for name in obj.keys()|sort %}
  {{ name|color(fg='yellow') }}: {{obj[name].value }} {% if obj[name].kms_key_id -%}{% filter color(fg='cyan') %}[SECURE:{{obj[name].kms_key_id}}]{% endfilter %}{% endif %}
{%- endfor %}
