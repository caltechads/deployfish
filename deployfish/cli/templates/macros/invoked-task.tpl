{% macro task_container(container) %}
arn                :      {{ container['containerArn'] }}
image              :      {{ container['image'] }}
image digest       :      {{ container['imageDigest'] }}
runtime id         :      {{ container['runtimeId'] }}
health             :      {{ container['healthStatus'] }}
{% if 'cpu' in container -%}
cpu                :      {{ container['cpu'] }}
{% endif -%}
{% if 'memory' in container -%}
memory             :      {{ container['memory'] }}
{% endif -%}
{% if 'memoryReservation' in container -%}
memoryReservation  :      {{ container['memoryReservation'] }}
{% endif -%}

last status        :      {{ container['lastStatus'] }}
{% if 'exitCode' in container -%}
exit code          :      {{ container['exitCode'] }}
{% endif -%}
{% if 'reason' in container -%}
reason             :      {{ container['reason'] }}
{% endif -%}
{% endmacro %}

{% macro status(obj) %}
desired status      :     {{ obj.data['desiredStatus'] }}
last status         :     {{ obj.data['lastStatus'] }}
{% if 'stopCode' in obj.data -%}
stop code           :     {{ obj.data['stopCode'] }}
{% endif -%}
{% if 'stoppedReason' in obj.data -%}
reason              :     {{ obj.data['stoppedReason'] }}
{% endif -%}
{% endmacro %}

{% macro timestamps(obj) %}
{% if 'createdAt' in obj.data -%}
created             :     {{ obj.data['createdAt'].strftime('%Y-%m-%d %H:%M:%S') }}
{% endif -%}
{% if 'startedAt' in obj.data -%}
started             :     {{ obj.data['startedAt'].strftime('%Y-%m-%d %H:%M:%S') }}
{% endif -%}
{% if 'connectivityAt' in obj.data -%}
connectivity        :     {{ obj.data['connectivityAt'].strftime('%Y-%m-%d %H:%M:%S') }}
{% endif -%}
{% if 'pullStartedAt' in obj.data -%}
pull started        :     {{ obj.data['pullStartedAt'].strftime('%Y-%m-%d %H:%M:%S') }}
{% endif -%}
{% if 'pullStoppedAt' in obj.data -%}
pull stopped        :     {{ obj.data['pullStoppedAt'].strftime('%Y-%m-%d %H:%M:%S') }}
{% endif -%}
{% if 'executionStoppedAt' in obj.data -%}
execution stopped   :     {{ obj.data['executionStoppedAt'].strftime('%Y-%m-%d %H:%M:%S') }}
{% endif -%}
{% if 'stoppingAt' in obj.data -%}
stopping at         :     {{ obj.data['stoppingAt'].strftime('%Y-%m-%d %H:%M:%S') }}
{% endif -%}
{% if 'stoppedAt' in obj.data -%}
stopped             :     {{ obj.data['stoppedAt'].strftime('%Y-%m-%d %H:%M:%S') }}
{% endif -%}
{% endmacro %}
