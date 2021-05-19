from .abstract import Manager, Model


# ----------------------------------------
# Managers
# ----------------------------------------


class CloudwatchAlarmManager(Manager):

    service = 'cloudwatch'

    def get(self, pk, **kwargs):
        response = self.client.describe_alarms(AlarmNames=[pk])
        if 'MetricAlarms' in response and response['MetricAlarms']:
            return CloudwatchAlarm(response['MetricAlarms'][0])
        else:
            raise CloudwatchAlarm.DoesNotExist('No Cloudwatch Alarm with name "{}" exists in AWS'.format(pk))

    def list(self, cluster, service):
        response = self.client.describe_alarms(AlarmNamePrefix=['{}-{}'.format(cluster, service)])
        if 'MetricAlarms' in response:
            return [CloudwatchAlarm(d) for d in response['MetricAlarms']]
        return []

    def save(self, obj):
        self.delete(obj)
        self.client.put_metric_alarm(**obj.render_for_create())

    def delete(self, obj):
        try:
            self.client.delete_alarms(AlarmNames=[obj.pk])
        except self.client.exceptions.ResourceNotFound:
            pass


# ----------------------------------------
# Models
# ----------------------------------------

class CloudwatchAlarm(Model):

    objects = CloudwatchAlarmManager()

    @property
    def pk(self):
        return self.data['AlarmName']

    @property
    def name(self):
        return self.data['AlarmName']

    @property
    def arn(self):
        return self.data.get('AlarmArn', None)

    def set_policy_arn(self, arn):
        self.data['AlarmActions'] = [arn]

    def render_for_diff(self):
        data = {}
        data['AlarmName'] = self.data['AlarmName']
        data['AlarmDescription'] = self.data['AlarmDescription']
        data['MetricName'] = self.data['MetricName']
        data['Namespace'] = self.data['Namespace']
        data['Statistic'] = self.data['Statistic']
        data['Dimensions'] = self.data['Dimensions']
        data['Period'] = self.data['Period']
        data['Unit'] = self.data['Unit']
        data['EvaluationPeriods'] = self.data['EvaluationPeriods']
        data['ComparisonOperator'] = self.data['ComparisonOperator']
        data['Threshold'] = self.data['Threshold']
        return data
