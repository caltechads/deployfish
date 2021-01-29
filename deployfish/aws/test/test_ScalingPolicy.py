import unittest
from copy import copy
from datetime import datetime
from mock import Mock
from testfixtures import Replacer

from deployfish.aws.appscaling import ScalingPolicy

YML = {
    'cpu': '>=60.5',
    'check_every_seconds': 60,
    'periods': 5,
    'cooldown': 60,
    'scale_by': 1
}


class TestScalingPolicy_load_yaml(unittest.TestCase):

    def setUp(self):
        aws_data = {
            'ScalingPolicies': [],
            'NextToken': None
        }
        metric_aws_data = {
            'MetricAlarms': [],
            'NextToken': None
        }
        appscaling_client = Mock()
        appscaling_client.describe_scaling_policies = Mock(return_value=aws_data)
        appscaling_client.describe_alarms = Mock(return_value=metric_aws_data)
        client = Mock(return_value=appscaling_client)
        self.init = Mock(return_value=None)
        with Replacer() as r:
            r.replace('boto3.client', client)
            self.policy = ScalingPolicy('my_service', 'my_cluster', YML)

    def tearDown(self):
        self.init.reset_mock()

    def test_exists(self):
        self.assertEqual(self.policy.exists(), False)

    def test_arn(self):
        self.assertEqual(self.policy.arn, None)

    def test_cpu(self):
        self.assertEqual(self.policy.cpu, ">=60.5")

    def test_name(self):
        self.assertEqual(self.policy.name, 'my_cluster-my_service-scale-up')

    def test_scale_by(self):
        self.assertEqual(self.policy.scale_by, 1)

    def test_cooldown(self):
        self.assertEqual(self.policy.cooldown, 60)

    def test_alarm(self):
        self.assertTrue(self.policy.alarm is not None)


class TestScalingPolicy_load_aws(unittest.TestCase):

    def setUp(self):
        aws_data = {
            'ScalingPolicies': [
                {
                    'PolicyARN': 'my_policy_arn',
                    'PolicyName': 'my_cluster-my_service-scale-up',
                    'ServiceNamespace': 'ecs',
                    'ResourceId': 'service/my_cluster/my_service',
                    'ScalableDimension': 'ecs:service:DesiredCount',
                    'PolicyType': 'StepScaling',
                    'StepScalingPolicyConfiguration': {
                        'AdjustmentType': 'ChangeInCapacity',
                        'StepAdjustments': [
                            {
                                'MetricIntervalLowerBound': 0,
                                'MetricIntervalUpperBound': None,
                                'ScalingAdjustment': 1
                            },
                        ],
                        'MinAdjustmentMagnitude': 1,
                        'Cooldown': 60,
                        'MetricAggregationType': 'Average',
                    },
                    'Alarms': [
                        {
                            'AlarmName': 'my_cluster-my_service-scale-up',
                            'AlarmARN': 'my_alarm_arn'
                        },
                    ],
                    'CreationTime': datetime(2015, 1, 1)
                },
            ],
            'NextToken': None
        }
        appscaling_client = Mock()
        appscaling_client.describe_scaling_policies = Mock(return_value=aws_data)
        client = Mock(return_value=appscaling_client)
        self.init = Mock(return_value=None)
        with Replacer() as r:
            r.replace('boto3.client', client)
            r.replace('deployfish.aws.cloudwatch.ECSServiceCPUAlarm.from_aws', Mock())
            self.policy = ScalingPolicy('my_service', 'my_cluster')

    def test_exists(self):
        self.assertEqual(self.policy.exists(), True)

    def test_arn(self):
        self.assertEqual(self.policy.arn, 'my_policy_arn')

    def test_cpu(self):
        self.assertEqual(self.policy.cpu, '')

    def test_name(self):
        self.assertEqual(self.policy.name, 'my_cluster-my_service-scale-up')

    def test_scale_by(self):
        self.assertEqual(self.policy.scale_by, 1)

    def test_cooldown(self):
        self.assertEqual(self.policy.cooldown, 60)


class TestScalingPolicy_load_aws_obj(unittest.TestCase):

    def setUp(self):
        aws_data = {
            'PolicyARN': 'my_policy_arn',
            'PolicyName': 'my_cluster-my_service-scale-up',
            'ServiceNamespace': 'ecs',
            'ResourceId': 'service/my_cluster/my_service',
            'ScalableDimension': 'ecs:service:DesiredCount',
            'PolicyType': 'StepScaling',
            'StepScalingPolicyConfiguration': {
                'AdjustmentType': 'ChangeInCapacity',
                'StepAdjustments': [
                    {
                        'MetricIntervalLowerBound': 60.5,
                        'MetricIntervalUpperBound': None,
                        'ScalingAdjustment': 1
                    },
                ],
                'MinAdjustmentMagnitude': 1,
                'Cooldown': 60,
                'MetricAggregationType': 'Average',
            },
            'Alarms': [
                {
                    'AlarmName': 'my_cluster-my_service-scale-up',
                    'AlarmARN': 'my_alarm_arn'
                },
            ],
            'CreationTime': datetime(2015, 1, 1)
        }
        appscaling_client = Mock()
        self.describe_scaling_policies = Mock()
        appscaling_client.describe_scaling_policies = self.describe_scaling_policies
        client = Mock(return_value=appscaling_client)
        self.init = Mock(return_value=None)
        with Replacer() as r:
            r.replace('boto3.client', client)
            self.policy = ScalingPolicy('my_service', 'my_cluster', aws=aws_data)

    def tearDown(self):
        self.init.reset_mock()

    def test_exists(self):
        self.assertEqual(self.policy.exists(), True)

    def test_arn(self):
        self.assertEqual(self.policy.arn, 'my_policy_arn')

    def test_cpu(self):
        self.assertEqual(self.policy.cpu, '')

    def test_name(self):
        self.assertEqual(self.policy.name, 'my_cluster-my_service-scale-up')

    def test_scale_by(self):
        self.assertEqual(self.policy.scale_by, 1)

    def test_cooldown(self):
        self.assertEqual(self.policy.cooldown, 60)

    def test_describe_scaling_policies_not_called(self):
        self.describe_scaling_policies.assert_not_called()


class TestScalingPolicy_render_create_scale_up(unittest.TestCase):

    def setUp(self):
        aws_data = {
            'ScalingPolicies': [],
            'NextToken': None
        }
        self.init = Mock(return_value=None)
        self.init.return_value = None
        appscaling_client = Mock()
        appscaling_client.describe_scaling_policies = Mock(return_value=aws_data)
        client = Mock(return_value=appscaling_client)
        self.init = Mock(return_value=None)
        with Replacer() as r:
            r.replace('boto3.client', client)
            r.replace('deployfish.aws.cloudwatch.ECSServiceCPUAlarm.__init__', self.init)
            self.policy = ScalingPolicy('my_service', 'my_cluster', YML)

    def tearDown(self):
        self.init.reset_mock()

    def test_PolicyName(self):
        self.assertEqual(self.policy._render_create()['PolicyName'], 'my_cluster-my_service-scale-up')

    def test_ServiceNamespace(self):
        self.assertEqual(self.policy._render_create()['ServiceNamespace'], 'ecs')

    def test_ResourceId(self):
        self.assertEqual(self.policy._render_create()['ResourceId'], 'service/my_cluster/my_service')

    def test_ScalableDimension(self):
        self.assertEqual(self.policy._render_create()['ScalableDimension'], 'ecs:service:DesiredCount')

    def test_PolicyType(self):
        self.assertEqual(self.policy._render_create()['PolicyType'], 'StepScaling')

    def test_MetricIntervalLowerBound(self):
        policy = self.policy._render_create()
        self.assertEqual(policy['StepScalingPolicyConfiguration']['StepAdjustments'][0]['MetricIntervalLowerBound'], 0)

    def test_NotHasMetricIntervalUpperBound(self):
        policy = self.policy._render_create()
        self.assertTrue(
            'MetricIntervalUpperBound' not in policy['StepScalingPolicyConfiguration']['StepAdjustments'][0]
        )

    def test_ScalingAdjustment(self):
        self.assertEqual(
            self.policy._render_create()['StepScalingPolicyConfiguration']['StepAdjustments'][0]['ScalingAdjustment'],
            1
        )

    def test_Cooldown(self):
        self.assertEqual(self.policy._render_create()['StepScalingPolicyConfiguration']['Cooldown'], 60)

    def test_MetricAggregationType(self):
        self.assertEqual(
            self.policy._render_create()['StepScalingPolicyConfiguration']['MetricAggregationType'], 'Average'
        )


class TestScalingPolicy_render_create_scale_down(unittest.TestCase):

    def setUp(self):
        aws_data = {
            'ScalingPolicies': [],
            'NextToken': None
        }
        self.init = Mock(return_value=None)
        self.init.return_value = None
        appscaling_client = Mock()
        appscaling_client.describe_scaling_policies = Mock(return_value=aws_data)
        client = Mock(return_value=appscaling_client)
        self.init = Mock(return_value=None)
        yml = copy(YML)
        yml['cpu'] = "<=30.4"
        yml['scale_by'] = -1
        with Replacer() as r:
            r.replace('boto3.client', client)
            r.replace('deployfish.aws.cloudwatch.ECSServiceCPUAlarm.__init__', self.init)
            self.policy = ScalingPolicy('my_service', 'my_cluster', yml)

    def test_NotHasMetricIntervalLowerBound(self):
        policy = self.policy._render_create()
        self.assertTrue(
            'MetricIntervalLowerBound' not in policy['StepScalingPolicyConfiguration']['StepAdjustments'][0]
        )

    def test_MetricIntervalUpperBound(self):
        policy = self.policy._render_create()
        self.assertEqual(policy['StepScalingPolicyConfiguration']['StepAdjustments'][0]['MetricIntervalUpperBound'], 0)

    def test_ScalingAdjustment(self):
        policy = self.policy._render_create()
        self.assertEqual(policy['StepScalingPolicyConfiguration']['StepAdjustments'][0]['ScalingAdjustment'], -1)
