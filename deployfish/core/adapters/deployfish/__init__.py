from deployfish.registry import registry
from .ecs import (
    ServiceAdapter,
    StandaloneTaskAdapter,
    TaskDefinitionAdapter,
)
from .events import (
    EventScheduleRuleAdapter,
    EventTargetAdapter,
)
from .cloudwatch import ECSServiceCPUAlarmAdapter
from .appscaling import (
    ECSServiceScalingPolicyAdapter,
    ECSServiceScalableTargetAdapter,
)
from .secrets import SecretAdapter
from .service_discovery import ServiceDiscoveryServiceAdapter


# -----------------------
# Adapter registrations
# -----------------------

# ecs
registry.register('StandaloneTask', 'deployfish', StandaloneTaskAdapter)
registry.register('TaskDefinition', 'deployfish', TaskDefinitionAdapter)
registry.register('Service', 'deployfish', ServiceAdapter)

# events
registry.register('EventTarget', 'deployfish', EventTargetAdapter)
registry.register('EventScheduleRule', 'deployfish', EventScheduleRuleAdapter)

# cloudwatch
registry.register('CloudwatchAlarm', 'deployfish', ECSServiceCPUAlarmAdapter)

# appscaling
registry.register('ScalingPolicy', 'deployfish', ECSServiceScalingPolicyAdapter)
registry.register('ScalableTarget', 'deployfish', ECSServiceScalableTargetAdapter)

# secrets
registry.register('Secret', 'deployfish', SecretAdapter)

# service_discovery
registry.register('ServiceDiscoveryService', 'deployfish', ServiceDiscoveryServiceAdapter)
