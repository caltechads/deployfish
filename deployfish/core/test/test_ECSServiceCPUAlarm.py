import unittest
from datetime import datetime
from mock import Mock
from testfixtures import Replacer, compare


from deployfish.aws.cloudwatch import ECSServiceCPUAlarm


class TestECSServiceCPUAlarm_load_yaml(unittest.TestCase):

    def setUp(self):
        yml = {
            'cpu': '>=60.5',
            'check_every_seconds': 60,
            'periods': 5
        }
        self.alarm = ECSServiceCPUAlarm('my_service', 'my_cluster', yml, scaling_policy_arn='my_arn')

    def test_exists(self):
        self.assertEqual(self.alarm.exists(), False)

    def test_arn(self):
        self.assertEqual(self.alarm.arn, None)

    def test_name(self):
        self.assertEqual(self.alarm.name, 'my_cluster-my_service-high')

    def test_cpu(self):
        self.assertEqual(self.alarm.cpu, ">=60.5")

    def test_check_every_seconds(self):
        self.assertEqual(self.alarm.check_every_seconds, 60)

    def test_check_every_periods(self):
        self.assertEqual(self.alarm.periods, 5)


class TestECSServiceCPUAlarm_load_aws(unittest.TestCase):

    def setUp(self):
        yml = {
            'cpu': '>=60',
            'check_every_seconds': 60,
            'periods': 5
        }
        aws_data = {
            'MetricAlarms': [
                {
                    'AlarmName': 'my_cluster-my_service-high',
                    'AlarmArn': 'actual_aws_alarm_arn',
                    'AlarmDescription': 'Scale up ECS service my_service in cluster my_cluster if Service Average CPU '
                                        'is >=60 for 300 seconds',
                    'AlarmConfigurationUpdatedTimestamp': datetime(2015, 1, 1),
                    'ActionsEnabled': True,
                    'OKActions': [],
                    'AlarmActions': [
                        'arn:aws:something:something',
                    ],
                    'InsufficientDataActions': [],
                    'StateValue': 'OK',
                    'StateReason': 'string',
                    'StateReasonData': 'string',
                    'StateUpdatedTimestamp': datetime(2015, 1, 1),
                    'MetricName': 'CPUUtilization',
                    'Namespace': 'AWS/ECS',
                    'Statistic': 'Average',
                    'Dimensions': [
                        {
                            'Name': 'ClusterName',
                            'Value': 'my_cluster'
                        },
                        {
                            'Name': 'ServiceName',
                            'Value': 'my_service'
                        },
                    ],
                    'Period': 60,
                    'Unit': 'Percent',
                    'EvaluationPeriods': 5,
                    'Threshold': 60.0,
                    'ComparisonOperator': 'GreaterThanOrEqualToThreshold'
                }
            ]
        }
        cloudwatch_client = Mock()
        cloudwatch_client.describe_alarms = Mock()
        cloudwatch_client.describe_alarms.return_value = aws_data
        cloudwatch_client.list_metrics = Mock()
        cloudwatch_client.list_metrics.return_value = {'Metrics': []}
        client = Mock()
        client.return_value = cloudwatch_client
        with Replacer() as r:
            r('boto3.client', client)
            self.alarm = ECSServiceCPUAlarm('my_service', 'my_cluster', yml)

    def test_arn(self):
        self.assertEqual(self.alarm.arn, 'actual_aws_alarm_arn')

    def test_name(self):
        self.assertEqual(self.alarm.name, 'my_cluster-my_service-high')

    def test_cpu(self):
        self.assertEqual(self.alarm.cpu, ">=60")

    def test_check_every_seconds(self):
        self.assertEqual(self.alarm.check_every_seconds, 60)

    def test_check_every_periods(self):
        self.assertEqual(self.alarm.periods, 5)


class TestECSServiceCPUAlarm_load_aws_obj(unittest.TestCase):

    def setUp(self):
        aws_data = {
            'AlarmName': 'my_cluster-my_service-high',
            'AlarmArn': 'actual_aws_alarm_arn',
            'AlarmDescription': 'Scale up ECS service my_service in cluster my_cluster if Service Average CPU '
                                'is >=60 for 300 seconds',
            'AlarmConfigurationUpdatedTimestamp': datetime(2015, 1, 1),
            'ActionsEnabled': True,
            'OKActions': [],
            'AlarmActions': [
                'arn:aws:something:something',
            ],
            'InsufficientDataActions': [],
            'StateValue': 'OK',
            'StateReason': 'string',
            'StateReasonData': 'string',
            'StateUpdatedTimestamp': datetime(2015, 1, 1),
            'MetricName': 'CPUUtilization',
            'Namespace': 'AWS/ECS',
            'Statistic': 'Average',
            'Dimensions': [
                {
                    'Name': 'ClusterName',
                    'Value': 'my_cluster'
                },
                {
                    'Name': 'ServiceName',
                    'Value': 'my_service'
                },
            ],
            'Period': 60,
            'Unit': 'Percent',
            'EvaluationPeriods': 5,
            'Threshold': 60.0,
            'ComparisonOperator': 'GreaterThanOrEqualToThreshold'
        }
        cloudwatch_client = Mock()
        self.describe_alarms = Mock()
        cloudwatch_client.describe_alarms = self.describe_alarms
        cloudwatch_client.describe_alarms.return_value = aws_data
        cloudwatch_client.list_metrics = Mock()
        cloudwatch_client.list_metrics.return_value = {'Metrics': []}
        client = Mock()
        client.return_value = cloudwatch_client
        with Replacer() as r:
            r('boto3.client', client)
            self.alarm = ECSServiceCPUAlarm('my_service', 'my_cluster', aws=aws_data)

    def test_arn(self):
        self.assertEqual(self.alarm.arn, 'actual_aws_alarm_arn')

    def test_name(self):
        self.assertEqual(self.alarm.name, 'my_cluster-my_service-high')

    def test_cpu(self):
        self.assertEqual(self.alarm.cpu, ">=60.0")

    def test_check_every_seconds(self):
        self.assertEqual(self.alarm.check_every_seconds, 60)

    def test_check_every_periods(self):
        self.assertEqual(self.alarm.periods, 5)

    def test_describe_alarms_not_called(self):
        self.describe_alarms.assert_not_called()


class TestECSServiceCPUAlarm__render_create(unittest.TestCase):

    def setUp(self):
        yml = {
            'cpu': '>=60.5',
            'check_every_seconds': 60,
            'periods': 5
        }
        self.alarm = ECSServiceCPUAlarm('my_service', 'my_cluster', yml, scaling_policy_arn='my_arn')

    def test_AlarmName(self):
        self.assertEqual(self.alarm._render_create()['AlarmName'], 'my_cluster-my_service-high')

    def test_AlarmActions(self):
        compare(self.alarm._render_create()['AlarmActions'], ['my_arn'])

    def test_AlarmDescription(self):
        self.assertEqual(
            self.alarm._render_create()['AlarmDescription'],
            'Scale up ECS service my_service in cluster my_cluster if service Average CPU is >=60.5 for 300 seconds'
        )

    def test_MetricName(self):
        self.assertEqual(self.alarm._render_create()['MetricName'], 'CPUUtilization')

    def test_Namespace(self):
        self.assertEqual(self.alarm._render_create()['Namespace'], 'AWS/ECS')

    def test_Statistic(self):
        self.assertEqual(self.alarm._render_create()['Statistic'], 'Average')

    def test_Dimensions(self):
        compare(
            self.alarm._render_create()['Dimensions'],
            [{'Name': 'ClusterName', 'Value': 'my_cluster'}, {'Name': 'ServiceName', 'Value': 'my_service'}]
        )

    def test_Period(self):
        self.assertEqual(self.alarm._render_create()['Period'], 60)

    def test_Unit(self):
        self.assertEqual(self.alarm._render_create()['Unit'], "Percent")

    def test_EvaluationPeriods(self):
        self.assertEqual(self.alarm._render_create()['EvaluationPeriods'], 5)

    def test_ComparisonOperator(self):
        self.assertEqual(self.alarm._render_create()['ComparisonOperator'], 'GreaterThanOrEqualToThreshold')

    def test_ComparisonOperatorGreaterThan(self):
        yml = {
            'cpu': '>60.5',
            'check_every_seconds': 60,
            'periods': 5
        }
        alarm = ECSServiceCPUAlarm('my_service', 'my_cluster', yml, scaling_policy_arn='my_arn')
        self.assertEqual(alarm._render_create()['ComparisonOperator'], 'GreaterThanThreshold')

    def test_ComparisonOperatorLessThanOrEqualTo(self):
        yml = {
            'cpu': '<=60.5',
            'check_every_seconds': 60,
            'periods': 5
        }
        alarm = ECSServiceCPUAlarm('my_service', 'my_cluster', yml, scaling_policy_arn='my_arn')
        self.assertEqual(alarm._render_create()['ComparisonOperator'], 'LessThanOrEqualToThreshold')

    def test_ComparisonOperatorLessThan(self):
        yml = {
            'cpu': '<60.5',
            'check_every_seconds': 60,
            'periods': 5
        }
        alarm = ECSServiceCPUAlarm('my_service', 'my_cluster', yml, scaling_policy_arn='my_arn')
        self.assertEqual(alarm._render_create()['ComparisonOperator'], 'LessThanThreshold')

    def test_Threshold(self):
        self.assertEqual(self.alarm._render_create()['Threshold'], 60.5)
