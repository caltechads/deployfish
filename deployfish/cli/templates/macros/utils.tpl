{#
============================================================================================
General macros for use in any template
============================================================================================
#}


{% macro heading(msg) %}
{%- filter section_title(fg='cyan', bold=True) %}{{msg}}{% endfilter -%}
{% endmacro %}

{% macro subsection(msg) %}
{%- filter color(fg='cyan', bold=True) %}{{ msg }}{% endfilter -%}
{% endmacro %}

{% macro subobject(label, name) %}
{% filter color(fg='green') %}{{ label }}: {% endfilter %}{{ name|color(fg='cyan', bold=True) -}}
{% endmacro %}

{% macro tags(tag_dict) %}
{{ subsection('tags') }}
{% for key, value in tag_dict.items() %}    {{ key|color(fg='yellow') }}: {{ value }}
{% endfor -%}
{% endmacro %}
