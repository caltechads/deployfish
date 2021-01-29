import re

from deployfish.aws import get_boto3_session


class ECSServiceCPUAlarm(object):
    """
    A Cloudwatch Metric Alarm on ECS Service CPU.
    """

    def __init__(self, serviceName, clusterName, yml=None, aws=None, scaling_policy_arn=None):
        """
        `yml` should be a dict with two keys:

            cpu: >=60
            check_every_seconds: 60
            periods: 5

        In this case, the alarm will examine the ECS Service CPU metric every 60 seconds.
        If service CPU >=60 for 5*60 seconds == 300 seconds, enter alarm state.

        :param serviceName: the name of the ECS service to monitor
        :type serviceName: string

        :param clusterName: the name of the cluster the service is in
        :type clusterName: string

        :param aws: (optional) the dict returned by ``describe_alarms()`` for this Alarm
        :type aws: dict

        :param scaling_policy_arn: (optional) the ARN of the scaling policy that should be activated when the alarm
                             enters ALARM state.
        :type scaling_policy_arn: string

        """
        if aws is None:
            aws = {}
        if yml is None:
            yml = {}
        self.cloudwatch = get_boto3_session().client('cloudwatch')
        self.serviceName = serviceName
        self.clusterName = clusterName
        self.scaling_policy_arn = scaling_policy_arn
        self.__defaults()
        self.from_yaml(yml)
        self.from_aws(aws)

    def __defaults(self):
        self._name = None
        self._cpu = None
        self._check_every_seconds = None
        self._periods = None
        self._unit = None
        self.__aws_alarm = {}

    def metric_exists(self):
        """
        Return `True` if the CPU metric for our ECS service exists in AWS.
        """
        response = self.cloudwatch.list_metrics(
            Namespace='AWS/ECS',
            MetricName='CPUUtilization',
            Dimensions=[
                {
                    'Name': 'ClusterName',
                    'Value': self.clusterName,
                },
                {
                    'Name': 'ServiceName',
                    'Value': self.serviceName,
                },
            ]
        )
        if response['Metrics']:
            return True
        raise False

    @property
    def arn(self):
        if self.exists():
            return self.__aws_alarm['AlarmArn']
        return None

    @property
    def name(self):
        if not self._name and self.exists():
            self.name = self.__aws_alarm['AlarmName']
        else:
            if '<' in self.cpu:
                direction = 'low'
            else:
                direction = 'high'
            self.name = '{}-{}-{}'.format(self.clusterName, self.serviceName, direction)
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def cpu(self):
        if not self._cpu and self.exists():
            # == should never actually get used, here.
            operator = '=='
            if self.__aws_alarm['ComparisonOperator'] == 'GreaterThanOrEqualToThreshold':
                operator = ">="
            elif self.__aws_alarm['ComparisonOperator'] == 'GreaterThanThreshold':
                operator = ">"
            elif self.__aws_alarm['ComparisonOperator'] == 'LessThanThreshold':
                operator = "<"
            elif self.__aws_alarm['ComparisonOperator'] == 'LessThanOrEqualToThreshold':
                operator = "<="
            self._cpu = "{}{}".format(operator, self.__aws_alarm['Threshold'])
        return self._cpu

    @cpu.setter
    def cpu(self, cpu):
        self._cpu = cpu

    @property
    def unit(self):
        if not self._unit and self.exists():
            self._unit = self.__aws_alarm['Unit']
        return self._unit

    @unit.setter
    def unit(self, unit):
        self._unit = unit

    @property
    def check_every_seconds(self):
        if not self._check_every_seconds and self.exists():
            self.check_every_seconds = self.__aws_alarm['Period']
        return self._check_every_seconds

    @check_every_seconds.setter
    def check_every_seconds(self, seconds):
        self._check_every_seconds = int(seconds)

    @property
    def periods(self):
        if not self._periods and self.exists():
            self.periods = self.__aws_alarm['EvaluationPeriods']
        return self._periods

    @periods.setter
    def periods(self, periods):
        self._periods = int(periods)

    def from_aws(self, aws=None):
        if aws is None:
            aws = {}
        self.__aws_alarm = {}
        if aws:
            self.__aws_alarm = aws
        else:
            response = self.cloudwatch.describe_alarms(AlarmNames=[self.name])
            if response['MetricAlarms']:
                self.__aws_alarm = response['MetricAlarms'][0]

    def from_yaml(self, yml):
        if yml:
            self.cpu = yml['cpu']
            self.check_every_seconds = yml['check_every_seconds']
            self.periods = yml['periods']
            self.unit = yml.get('unit', 'Percent')

    def exists(self):
        """
        Return ``True`` if this alarm exists in AWS, ``False`` otherwise.

        :rtype: boolean
        """
        if self.__aws_alarm:
            return True
        return False

    def _render_create(self):
        """
        Return the argument list to pass to boto3's ``put_metric_alarm()``.

        :rtype: dict
        """
        r = {'AlarmName': self.name}
        if '>' in self.cpu:
            direction = 'up'
        else:
            direction = 'down'
        r['AlarmDescription'] = (
            "Scale {} ECS service {} in cluster {} if service Average CPU is {} for {} seconds".format(
                direction,
                self.serviceName,
                self.clusterName,
                self.cpu,
                (self.periods * self.check_every_seconds)
            )
        )
        r['AlarmActions'] = [self.scaling_policy_arn]
        r['MetricName'] = 'CPUUtilization'
        r['Namespace'] = 'AWS/ECS'
        r['Statistic'] = 'Average'
        r['Dimensions'] = [
            {'Name': 'ClusterName', 'Value': self.clusterName},
            {'Name': 'ServiceName', 'Value': self.serviceName}
        ]
        r['Period'] = self.check_every_seconds
        r['Unit'] = self.unit
        r['EvaluationPeriods'] = self.periods
        operator = '=='
        if '<=' in self.cpu:
            operator = "LessThanOrEqualToThreshold"
        elif '<' in self.cpu:
            operator = "LessThanThreshold"
        elif '>=' in self.cpu:
            operator = "GreaterThanOrEqualToThreshold"
        elif '>' in self.cpu:
            operator = "GreaterThanThreshold"
        r['ComparisonOperator'] = operator
        r['Threshold'] = float(re.sub('[<>=]*', '', self.cpu))
        return r

    def _render_delete(self):
        """
        Return the argument list to pass to boto3's ``delete_alarms()``.

        :rtype: dict
        """
        return {'AlarmNames': [self.name]}

    def __eq__(self, other):
        if (self.name == other.name and
            self.cpu == other.cpu and
            self.check_every_seconds == other.check_every_seconds and
            self.periods == other.periods and
            self.scaling_policy_arn == other.scaling_policy_arn and
            self.unit == other.unit
        ):
            return True
        return False

    def __ne__(self, other):
        return not self == other

    def create(self):
        self.cloudwatch.put_metric_alarm(**self._render_create())

    def delete(self):
        if self.exists():
            self.cloudwatch.delete_alarms(**self._render_delete())
            self.__aws_alarm = {}

    def needs_update(self):
        return self != ECSServiceCPUAlarm(self.serviceName, self.clusterName, aws=self.__aws_alarm)

    def update(self):
        if self != ECSServiceCPUAlarm(self.serviceName, self.clusterName, aws=self.__aws_alarm):
            self.delete()
            self.create()
