from typing import Dict, Any, Tuple, Optional

from ..abstract import Adapter
from deployfish.core.models import CloudwatchAlarm, ScalingPolicy


# ------------------------
# Adapters
# ------------------------

class ECSServiceScalingPolicyAdapter(Adapter):
    """
        {
            'cpu': '>=60',
            'check_every_seconds': 60,
            'periods': 5,
            'cooldown': 60,
            'scale_by': 1
        }
    """

    def __init__(self, data: Dict[str, Any], **kwargs) -> None:
        self.cluster = kwargs.pop('cluster', None)
        self.service = kwargs.pop('service', None)
        super().__init__(data, **kwargs)

    def get_PolicyName(self) -> str:
        if int(self.data['scale_by']) < 0:
            direction = 'scale-down'
        else:
            direction = 'scale-up'
        return '{}-{}-{}'.format(self.cluster, self.service, direction)

    def get_ResourceId(self) -> str:
        return 'service/{}/{}'.format(self.cluster, self.service)

    def get_MetricIntervalLowerBound(self) -> Optional[float]:
        if '>' in self.data['cpu']:
            return 0.0
        return None

    def get_MetricIntervalUpperBound(self) -> Optional[float]:
        if '<' in self.data['cpu']:
            return 0.0
        return None

    def convert(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        data: Dict[str, Any] = {}
        data['PolicyName'] = self.get_PolicyName()
        data['ServiceNamespace'] = 'ecs'
        data['ResourceId'] = self.get_ResourceId()
        data['ScalableDimension'] = 'ecs:service:DesiredCount'
        data['PolicyType'] = 'StepScaling'
        adjustment: Dict[str, Any] = {'ScalingAdjustment': int(self.data['scale_by'])}
        lower_bound = self.get_MetricIntervalLowerBound()
        if lower_bound is not None:
            adjustment['MetricIntervalLowerBound'] = lower_bound
        upper_bound = self.get_MetricIntervalUpperBound()
        if upper_bound is not None:
            adjustment['MetricIntervalUpperBound'] = upper_bound
        data['StepScalingPolicyConfiguration'] = {
            'AdjustmentType': 'ChangeInCapacity',
            'StepAdjustments': [adjustment],
            'Cooldown': int(self.data['cooldown']),
            'MetricAggregationType': 'Average'
        }
        kwargs = {}
        kwargs['alarm'] = CloudwatchAlarm.new(
            self.data,
            'deployfish',
            cluster=self.cluster,
            service=self.service
        )
        return data, kwargs


class ECSServiceScalableTargetAdapter(Adapter):
    """
        {
            'min_capacity': 2,
            'max_capacity': 4,
            'role_arn': 'arn:aws:iam::123445678901:role/ecsServiceRole',
            'scale-up': {
                'cpu': '>=60',
                'check_every_seconds': 60,
                'periods': 5,
                'cooldown': 60,
                'scale_by': 1
            },
            'scale-down': {
                'cpu': '<=30',
                'check_every_seconds': 60,
                'periods': 30,
                'cooldown': 60,
                'scale_by': -1
            }
        }
    """

    def __init__(self, data: Dict[str, Any], **kwargs):
        self.cluster = kwargs.pop('cluster', None)
        self.service = kwargs.pop('service', None)
        super().__init__(data, **kwargs)

    def get_ResourceId(self) -> str:
        return 'service/{}/{}'.format(self.cluster, self.service)

    def convert(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        data = {}
        data['ServiceNamespace'] = 'ecs'
        data['ResourceId'] = self.get_ResourceId()
        data['ScalableDimension'] = 'ecs:service:DesiredCount'
        data['MinCapacity'] = self.data['min_capacity']
        data['MaxCapacity'] = self.data['max_capacity']
        data['RoleARN'] = self.data['role_arn']
        kwargs = {}
        policies = []
        policies.append(ScalingPolicy.new(
            self.data['scale-up'],
            'deployfish',
            cluster=self.cluster,
            service=self.service
        ))
        policies.append(ScalingPolicy.new(
            self.data['scale-down'],
            'deployfish',
            cluster=self.cluster,
            service=self.service
        ))
        kwargs['policies'] = policies
        return data, kwargs
