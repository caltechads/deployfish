import re

from ..abstract import Adapter


# ------------------------
# Adapters
# ------------------------

class ECSServiceCPUAlarmAdapter(Adapter):
    """
        {
            'cpu': '>=60',
            'check_every_seconds': 60,
            'periods': 5,
            'cooldown': 60,
            'scale_by': 1
        }
    """

    def __init__(self, data, **kwargs):
        self.cluster = kwargs.pop('cluster', None)
        self.service = kwargs.pop('service', None)
        super(ECSServiceCPUAlarmAdapter, self).__init__(data, **kwargs)

    def get_AlarmName(self):
        if '<' in self.data['cpu']:
            direction = 'low'
        else:
            direction = 'high'
        return '{}-{}-{}'.format(self.cluster, self.service, direction)

    def get_AlarmDescription(self):
        if '>' in self.data['cpu']:
            direction = 'up'
        else:
            direction = 'down'
        return "Scale {} ECS service {} in cluster {} if service Average CPU is {} for {} seconds".format(
            direction,
            self.service,
            self.cluster,
            self.data['cpu'],
            (int(self.data['periods']) * int(self.data['check_every_seconds']))
        )

    def get_ComparisonOperator(self):
        operator = '=='
        if '<=' in self.data['cpu']:
            operator = "LessThanOrEqualToThreshold"
        elif '<' in self.data['cpu']:
            operator = "LessThanThreshold"
        elif '>=' in self.data['cpu']:
            operator = "GreaterThanOrEqualToThreshold"
        elif '>' in self.data['cpu']:
            operator = "GreaterThanThreshold"
        return operator

    def get_Threshold(self):
        return float(re.sub('[<>=]*', '', self.data['cpu']))

    def convert(self):
        data = {}
        data['AlarmName'] = self.get_AlarmName()
        data['AlarmDescription'] = self.get_AlarmDescription()
        data['MetricName'] = 'CPUUtilization'
        data['Namespace'] = 'AWS/ECS'
        data['Statistic'] = 'Average'
        data['Dimensions'] = [
            {'Name': 'ClusterName', 'Value': self.cluster},
            {'Name': 'ServiceName', 'Value': self.service}
        ]
        data['Period'] = int(self.data['check_every_seconds'])
        data['Unit'] = self.data.get('unit', 'Percent')
        data['EvaluationPeriods'] = int(self.data['periods'])
        data['ComparisonOperator'] = self.get_ComparisonOperator()
        return data, {}
