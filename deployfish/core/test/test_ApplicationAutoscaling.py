import unittest
from datetime import datetime
from mock import Mock
from testfixtures import Replacer, compare


from deployfish.aws.appscaling import ApplicationAutoscaling

YML = {
    'min_capacity': 2,
    'max_capacity': 4,
    'role_arn': 'arn:aws:iam::123445678901:role/ecsServiceRole',
    'scale-up':  {
        'cpu': '>=60.5',
        'check_every_seconds': 60,
        'periods': 5,
        'cooldown': 60,
        'scale_by': 1
    },
    'scale-down':  {
        'cpu': '<=30.2',
        'check_every_seconds': 60,
        'periods': 5,
        'cooldown': 60,
        'scale_by': -1
    },
}


class TestApplicationAutoscaling_load_yaml(unittest.TestCase):

    def setUp(self):
        self.init = Mock(return_value=None)
        with Replacer() as r:
            r.replace('deployfish.aws.appscaling.ScalingPolicy.__init__', self.init)
            self.appscaling = ApplicationAutoscaling('my_service', 'my_cluster', YML)

    def tearDown(self):
        self.init.reset_mock()

    def test_should_exist(self):
        self.assertEqual(self.appscaling.should_exist(), True)

    def test_exists(self):
        self.assertEqual(self.appscaling.exists(), False)

    def test_resource_id(self):
        self.assertEqual(self.appscaling.resource_id, 'service/my_cluster/my_service')

    def test_MinCapacity(self):
        self.assertEqual(self.appscaling.MinCapacity, 2)

    def test_MaxCapacity(self):
        self.assertEqual(self.appscaling.MaxCapacity, 4)

    def test_RoleARN(self):
        self.assertEqual(self.appscaling.RoleARN, 'arn:aws:iam::123445678901:role/ecsServiceRole')

    def test_policies(self):
        self.assertEqual(len(self.appscaling.policies), 2)
        self.assertTrue('scale-up' in self.appscaling.policies)
        self.assertTrue('scale-down' in self.appscaling.policies)
        self.init.assert_any_call('my_service', 'my_cluster', YML['scale-up'])
        self.init.assert_any_call('my_service', 'my_cluster', YML['scale-down'])


class TestApplicationAutoscaling__render_create(unittest.TestCase):

    def setUp(self):
        self.init = Mock(return_value=None)
        with Replacer() as r:
            r.replace('deployfish.aws.appscaling.ScalingPolicy.__init__', self.init)
            self.appscaling = ApplicationAutoscaling('my_service', 'my_cluster', YML)

    def test_ServiceNamespace(self):
        self.assertEqual(self.appscaling._render_create()['ServiceNamespace'], 'ecs')

    def test_ResourceId(self):
        compare(self.appscaling._render_create()['ResourceId'], 'service/my_cluster/my_service')

    def test_ScalableDimension(self):
        compare(self.appscaling._render_create()['ScalableDimension'], 'ecs:service:DesiredCount')

    def test_MinCapacity(self):
        compare(self.appscaling._render_create()['MinCapacity'], 2)

    def test_MaxCapacity(self):
        compare(self.appscaling._render_create()['MaxCapacity'], 4)

    def test_RoleARN(self):
        compare(self.appscaling._render_create()['RoleARN'], 'arn:aws:iam::123445678901:role/ecsServiceRole')


class TestApplicationAutoscaling__from_aws(unittest.TestCase):

    def setUp(self):
        aws_data = {
            'ScalableTargets': [
                {
                    'ServiceNamespace': 'ecs',
                    'ResourceId': 'service/my_cluster/my_service',
                    'ScalableDimension': 'ecs:service:DesiredCount',
                    'MinCapacity': 1,
                    'MaxCapacity': 3,
                    'RoleARN': 'my_role_arn',
                    'CreationTime': datetime(2017, 4, 14)
                }
            ],
            'NextToken': None
        }
        init = Mock(return_value=None)
        init.return_value = None
        appscaling_client = Mock()
        appscaling_client.describe_scalable_targets = Mock(return_value=aws_data)
        client = Mock(return_value=appscaling_client)
        with Replacer() as r:
            r.replace('boto3.client', client)
            r.replace('deployfish.aws.appscaling.ScalingPolicy.__init__', init)
            self.appscaling = ApplicationAutoscaling('my_service', 'my_cluster')

    def test_should_exist(self):
        self.assertEqual(self.appscaling.should_exist(), False)

    def test_exists(self):
        self.assertEqual(self.appscaling.exists(), True)

    def test_resource_id(self):
        self.assertEqual(self.appscaling.resource_id, 'service/my_cluster/my_service')

    def test_MinCapacity(self):
        self.assertEqual(self.appscaling.MinCapacity, 1)

    def test_MaxCapacity(self):
        self.assertEqual(self.appscaling.MaxCapacity, 3)

    def test_RoleARN(self):
        self.assertEqual(self.appscaling.RoleARN, 'my_role_arn')


class TestApplicationAutoscaling__from_aws_dict(unittest.TestCase):

    def setUp(self):
        aws_data = {
            'ServiceNamespace': 'ecs',
            'ResourceId': 'service/my_cluster/my_service',
            'ScalableDimension': 'ecs:service:DesiredCount',
            'MinCapacity': 1,
            'MaxCapacity': 3,
            'RoleARN': 'my_role_arn',
            'CreationTime': datetime(2017, 4, 14)
        }
        init = Mock(return_value=None)
        init.return_value = None
        appscaling_client = Mock()
        self.describe_scaling_targets = Mock(return_value=aws_data)
        appscaling_client.describe_scalable_targets = self.describe_scaling_targets
        client = Mock(return_value=appscaling_client)
        with Replacer() as r:
            r.replace('boto3.client', client)
            r.replace('deployfish.aws.appscaling.ScalingPolicy.__init__', init)
            self.appscaling = ApplicationAutoscaling('my_service', 'my_cluster', aws=aws_data)

    def test_should_exist(self):
        self.assertEqual(self.appscaling.should_exist(), False)

    def test_exists(self):
        self.assertEqual(self.appscaling.exists(), True)

    def test_resource_id(self):
        self.assertEqual(self.appscaling.resource_id, 'service/my_cluster/my_service')

    def test_MinCapacity(self):
        self.assertEqual(self.appscaling.MinCapacity, 1)

    def test_MaxCapacity(self):
        self.assertEqual(self.appscaling.MaxCapacity, 3)

    def test_RoleARN(self):
        self.assertEqual(self.appscaling.RoleARN, 'my_role_arn')

    def test_describe_scaling_targets_not_called(self):
        self.describe_scaling_targets.assert_not_called()
