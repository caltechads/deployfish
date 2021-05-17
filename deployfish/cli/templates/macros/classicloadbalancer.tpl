{% macro elb_health_check(elb) %}
target            :     {{ elb.data['HealthCheck']['Target'] }}
interval          :     {{ elb.data['HealthCheck']['Interval'] }}
timeout           :     {{ elb.data['HealthCheck']['Timeout'] }}
unhealthy count   :     {{ elb.data['HealthCheck']['UnhealthyThreshold'] }}
healthy count     :     {{ elb.data['HealthCheck']['HealthyThreshold'] }}
{% endmacro %}
