{% macro volume(obj) %}
{%- if 'host' in obj %}
source path     :     {{ obj['host']['sourcePath'] }}
{%- endif %}
{%- if 'dockerVolumeConfiguration' in obj %}
{% filter color(fg='cyan') %}config: {% endfilter %}
{# Render the dockerVolumeConfiguration for a task volume #}
  scope         :     {{ obj['dockerVolumeConfiguration']['scope'] }}
{%- if obj['dockerVolumeConfiguration']['scope'] == 'shared' %}
  autoprovision :     {{ obj['dockerVolumeConfiguration']['autoprovision'] }}
{%- endif %}
  driver options
{%- for key, value in obj['dockerVolumeConfiguration']['driverOpts'] %}
    {{ key }}: {{ value }}
{%- endfor %}
{% endif -%}
{% endmacro %}

{# Render the list of port mappings for a container #}
{% macro ports(portMappings) %}
{%- filter color(fg='cyan', bold=True) %}ports{% endfilter %}
{% for port in portMappings -%}
{%- if 'containerPort' in port and port.get('hostPort', None) != '0' -%}
{{ port['containerPort'] }}/{{ port['protocol'] }}
{% else -%}
{{ port['hostPort'] }}:{{ port['containerPort'] }}/{{ port['protocol'] }}
{% endif -%}
{%- endfor -%}
{% endmacro %}

{# Render the list of mount points for a container #}
{% macro mountpoints(objs) %}
{%- filter color(fg='cyan', bold=True) %}mount points{% endfilter %}
{% for mp in objs -%}
{{ mp['sourceVolume'] }}:{{ mp['containerPath'] }}{% if 'readOnly' in mp and mp['readOnly'] %}:ro{% endif %}
{%- endfor -%}
{% endmacro %}

{# Render the list of environment variables for a container #}
{% macro environment(objs) %}
{%- filter color(fg='cyan', bold=True) %}environment{% endfilter %}
{{ objs|tabular(Name='name', Value='value', tablefmt='presto', show_headers=False) }}
{% endmacro %}

{# Render the list of secrets for a container #}
{% macro secrets(objs) %}
{%- filter color(fg='cyan', bold=True) %}secrets{% endfilter %}
{{ objs|tabular(Name='name', From='valueFrom', tablefmt='presto', show_headers=False, ordering='Name') }}
{% endmacro %}

{# Render the list of links for a container #}
{% macro links(objs) %}
{%- filter color(fg='cyan', bold=True) %}links{% endfilter %}
{% for link in objs -%}
{{ link }}
{%- endfor -%}
{% endmacro %}

{# Render the list of extraHosts for a container #}
{% macro extra_hosts(objs) %}
{%- filter color(fg='cyan', bold=True) %}extra hosts{% endfilter %}
{{ objs|tabular(Hostname='hostname', IpAddress='ipAddress', tablefmt='presto', show_headers=False, ordering='Hostname') }}
{% endmacro %}

{# Render the list of ulimits for a container #}
{% macro ulimits(objs) %}
{%- filter color(fg='cyan', bold=True) %}ulimits{% endfilter %}
{{ objs|tabular(Name='name', Soft_Limit='softLimit', Hard_Limit='hardLimit', tablefmt='simple', ordering='Name') }}
{% endmacro %}

{# Render a container definition #}
{% macro container(obj) %}
image              :     {{ obj.data['image'] }}
{%- if 'cpu' in obj.data %}
cpu                :     {{ obj.data['cpu'] }}
{%- endif %}
{%- if 'memory' in obj.data %}
memory             :     {{ obj.data['memory'] }}
{%- endif %}
{%- if 'memoryReservation' in obj.data %}
memoryReservation  :     {{ obj.data['memoryReservation'] }}
{%- endif %}
{%- if 'entryPoint' in obj.data %}
entrypoint         :     {{ obj.data['entryPoint']|join('  ') }}
{%- endif %}
{%- if 'command' in obj.data %}
command            :     {{ obj.data['command']|join('  ') }}
{%- endif %}
{% if 'links' in obj.data -%}
{{ links(obj.data['links'])|indent }}
{%- endif -%}
{% if 'extraHosts' in obj.data -%}
{{ extra_hosts(obj.data['extraHosts'])|indent }}
{%- endif -%}
{% if 'ulimits' in obj.data -%}
{{ ulimits(obj.data['ulimits'])|indent }}
{%- endif -%}
{% if 'portMappings' in obj.data -%}
{{ ports(obj.data['portMappings'])|indent }}
{%- endif -%}
{% if 'mountPoints' in obj.data and obj.data['mountPoints'] -%}
{{ mountpoints(obj.data['mountPoints'])|indent }}
{%- endif %}
{% if 'environment' in obj.data and obj.data['environment'] -%}
{{ environment(obj.data['environment'])|indent(width=3) }}
{%- endif %}
{%- if 'secrets' in obj.data and obj.data['secrets'] -%}
{{ secrets(obj.data['secrets'])|indent(width=3) }}
{%- endif %}
{% endmacro %}

{# --------------------------------------------------------------------------- #}

{% macro task_definition(obj) %}
arn                 :     {{ obj.arn }}
family              :     {{ obj.family }}
revision            :     {{ obj.data['revision'] }}
{%- if 'requiresComptibilites' in obj.data %}
launch type         :     {{ obj.data['requiresCompatibilities']|join(', ') }}
{%- endif %}
network mode        :     {{ obj.data['networkMode'] }}
{%- if 'cpu' in obj.data %}
task cpu            :     {{ obj.data['cpu'] }}
{%- endif %}
{%- if 'memory' in obj.data %}
task memory         :     {{ obj.data['memory'] }}
{%- endif %}
{%- if 'volumes' in obj.data and obj.data['volumes'] %}

{% for volume_def in obj.data['volumes'] -%}
{% filter color(fg='green') %}Volume: {% endfilter %}{{ volume_def['name']|color(fg='cyan', bold=True) }}
{{- volume(volume_def)|indent(width=2) }}
{%- endfor -%}
{%- endif %}

{% for container_obj in obj.containers -%}
{% filter color(fg='green') %}Container: {% endfilter %}{{ container_obj.name|color(fg='cyan', bold=True) }}
{{- container(container_obj)|indent(width=2) }}
{%- endfor -%}
{% endmacro %}

