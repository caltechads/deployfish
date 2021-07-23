{% from 'macros/secrets.tpl' import secrets_table -%}
{% include 'standalonetask--detail:short.tpl' %}
{%- if includes is not defined or ('secrets' in includes and obj.secrets) %}
{% filter section_title(fg='cyan', bold=True) %}Secrets{% endfilter %}
{{ secrets_table(obj.secrets.values()) }}
{% endif -%}
