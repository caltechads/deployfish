{#
============================================================================================
Macros related to rendering TaskDefinitions, ContainerDefinitions and all their various bits
============================================================================================
#}

{% from 'macros/utils.tpl' import subsection, subobject %}

{# Render the list of volumes for a task definition #}
{# ------------------------------------------------ #}
{% macro volume(obj) %}
{%- if 'host' in obj %}
type            :     host
source path     :     {{ obj['host']['sourcePath'] }}
{%- endif %}
{%- if 'dockerVolumeConfiguration' in obj %}
type            :     docker
{{- subsection('config:') }}
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
{%- if 'efsVolumeConfiguration' in obj %}
type          :     EFS
name          :     {{ obj['efsVolumeConfiguration']['FileSystem'].name }}
id            :     {{ obj['efsVolumeConfiguration']['fileSystemId'] }}
arn           :     {{ obj['efsVolumeConfiguration']['FileSystem'].arn }}
created       :     {{ obj['efsVolumeConfiguration']['FileSystem'].data['CreationTime'] }}
size          :     {{ obj['efsVolumeConfiguration']['FileSystem'].size|filesizeformat }}
state         :     {{ obj['efsVolumeConfiguration']['FileSystem'].state }}
rootDirectory :     {{ obj['efsVolumeConfiguration']['rootDirectory'] }}
{% endif -%}
{% endmacro %}

{# Render the list of port mappings for a container #}
{# ------------------------------------------------ #}
{% macro ports(portMappings) %}
{{- subsection('ports') }}
{% for port in portMappings -%}
{%- if 'containerPort' in port and port.get('hostPort', None) != '0' -%}
{{ port['containerPort'] }}/{{ port['protocol'] }}
{% else -%}
{{ port['hostPort'] }}:{{ port['containerPort'] }}/{{ port['protocol'] }}
{% endif -%}
{%- endfor -%}
{% endmacro %}

{# Render the list of mount points for a container #}
{# ----------------------------------------------- #}
{% macro mountpoints(objs) %}
{{- subsection('mount points') }}
{% for mp in objs -%}
{{ mp['sourceVolume'] }}:{{ mp['containerPath'] }}{% if 'readOnly' in mp and mp['readOnly'] %}:ro{% endif %}
{%- endfor -%}
{% endmacro %}

{# Render the list of environment variables for a container #}
{# -------------------------------------------------------- #}
{% macro environment(objs) %}
{{- subsection('environment') }}
{{ objs|tabular(Name='name', Value='value', tablefmt='presto', show_headers=False) }}
{% endmacro %}

{# Render the list of secrets for a container #}
{# ------------------------------------------ #}
{% macro secrets(objs) %}
{{- subsection('secrets') }}
{{ objs|tabular(Name='name', From='valueFrom', tablefmt='presto', show_headers=False, ordering='Name') }}
{% endmacro %}

{# Render the list of links for a container #}
{# ---------------------------------------- #}
{% macro links(objs) %}
{{- subsection('links') }}
{% for link in objs -%}
{{ link }}
{%- endfor -%}
{% endmacro %}

{# Render the list of extraHosts for a container #}
{# --------------------------------------------- #}
{% macro extra_hosts(objs) %}
{{- subsection('extra hosts') }}
{{ objs|tabular(Hostname='hostname', IpAddress='ipAddress', tablefmt='presto', show_headers=False, ordering='Hostname') }}
{% endmacro %}

{# Render the list of ulimits for a container #}
{# ------------------------------------------ #}
{% macro ulimits(objs) %}
{{- subsection('ulimits') }}
{{ objs|tabular(Name='name', Soft_Limit='softLimit', Hard_Limit='hardLimit', tablefmt='simple', ordering='Name') }}
{% endmacro %}

{# Render the list of linuxParameters:capabilities for a container #}
{# --------------------------------------------------------------- #}
{% macro capabilities(obj) %}
{{- subsection('capabilities') }}
{% if 'add' in obj -%}
{% filter color(fg='green') %}ADD: {% endfilter %}{{ obj['add']|join(', ') }}
{% endif -%}
{% if 'drop' in obj -%}
{% filter color(fg='green') %}DROP: {% endfilter %}{{ obj['drop']|join(', ') }}
{% endif -%}
{% endmacro %}

{# Render the list of linuxParameters:tmpfs settings for a container #}
{# ----------------------------------------------------------------- #}
{% macro tmpfs(obj) %}
{{- subsection('tmpfs') }}
path          :     {{ obj['containerPath'] }}
size          :     {{ obj['size'] }}
{%- if 'mountOptions' in obj %}
mount options :     {{ obj['mountOptions']|join(',') }}
{%- endif %}
{% endmacro %}

{# Render a ContainerDefinition #}
{# ---------------------------- #}
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
{% if 'linuxParameters' in obj.data and 'capabilities' in obj.data['linuxParameters'] -%}
{{ capabilities(obj.data['linuxParameters']['capabilities'])|indent }}
{%- endif -%}
{% if 'portMappings' in obj.data and obj.data['portMappings'] -%}
{{ ports(obj.data['portMappings'])|indent }}
{%- endif -%}
{% if 'linuxParameters' in obj.data and 'tmpfs' in obj.data['linuxParameters'] -%}
{{ tmpfs(obj.data['linuxParameters']['tmpfs'])|indent }}
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
{# --------------------------------------------------------------------------- #}

{# Render a TaskDefinition #}
{# ----------------------- #}
{% macro task_definition(obj) %}
arn                 :     {{ obj.arn }}
family              :     {{ obj.family }}
revision            :     {{ obj.data['revision'] }}
{%- if 'taskRoleArn' in obj.data %}
task role           :     {{ obj.data['taskRoleArn'] }}
{%- endif %}
{%- if 'executionRoleArn' in obj.data %}
execution role      :     {{ obj.data['executionRoleArn'] }}
{%- endif %}
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

{% for volume_def in obj.render_for_display()['volumes'] -%}
{{ subobject('Volume', volume_def['name']) }}
{{- volume(volume_def)|indent(width=2) }}
{%- endfor -%}
{%- endif %}
{% for container_obj in obj.containers -%}
{{ subobject('Container', container_obj.name) }}
{{- container(container_obj)|indent(width=2) }}
{%- endfor -%}
{% endmacro %}

