from copy import deepcopy
import logging
import os
import unittest
from unittest.mock import Mock

from testfixtures import Replacer

from deployfish.exceptions import SchemaException  # noqa:F401
import deployfish.core.adapters  # noqa:F401
from deployfish.core.adapters import StandaloneTaskAdapter
from deployfish.core.models import Cluster


logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)

EC2_TASK_YML = {
    'name': 'foobar-test-mytask',
    'cluster': 'foobar-cluster',
    'service': 'foobar-cluster:foobar-test',
    'environment': 'test',
    'count': 1,
    'family': 'foobar-test-mytask',
    'network_mode': 'bridge',
    'task_role_arn': 'MY_TASK_ROLE_ARN',
    'execution_role': 'MY_EXECUTION_ROLE_ARN',
    'containers': [
        {
            'name': 'foobar',
            'image': 'foobar/foobar:0.1.0',
            'cpu': 512,
            'memory': 512,
            'environment': [
                'AWS_DEFAULT_REGION=us-west-2'
            ],
            'logging': {
                'driver': 'awslogs',
                'options': {
                    'awslog-group': 'my_log_group',
                    'awslog-stream': 'my_log_stream',
                    'awslog-region': 'us-west-2'
                }
            }
        }
    ],
    'config': [
        'DEBUG=False'
        'DB_HOST=my_rds_host',
        'DB_NAME=foobar',
        'DB_USER=foobar_u',
        'DB_PASSWORD=the_db_password',
        'DJANGO_SECRET_KEY=the_secret_key',
        'XFF_TRUSTED_PROXY_DEPTH=4',
        'STATSD_HOST=statsd.example.com',
        'STATSD_PREFIX=foobar.test',
    ]
}

FARGATE_TASK_YML = {
    'name': 'foobar-test-mytask',
    'cluster': 'foobar-cluster',
    'service': 'foobar-cluster:foobar-test',
    'environment': 'test',
    'launch_type': 'FARGATE',
    'count': 1,
    'family': 'foobar-test-mytask',
    'network_mode': 'bridge',
    'task_role_arn': 'MY_TASK_ROLE_ARN',
    'execution_role': 'MY_EXECUTION_ROLE_ARN',
    'containers': [
        {
            'name': 'foobar',
            'image': 'foobar/foobar:0.1.0',
            'cpu': 512,
            'memory': 512,
            'environment': [
                'AWS_DEFAULT_REGION=us-west-2'
            ],
            'logging': {
                'driver': 'awslogs',
                'options': {
                    'awslog-group': 'my_log_group',
                    'awslog-stream': 'my_log_stream',
                    'awslog-region': 'us-west-2'
                }
            }
        }
    ],
    'config': [
        'DEBUG=False'
        'DB_HOST=my_rds_host',
        'DB_NAME=foobar',
        'DB_USER=foobar_u',
        'DB_PASSWORD=the_db_password',
        'DJANGO_SECRET_KEY=the_secret_key',
        'XFF_TRUSTED_PROXY_DEPTH=4',
        'STATSD_HOST=statsd.example.com',
        'STATSD_PREFIX=foobar.test',
    ]
}


class BaseTestStandaloneTaskAdapter_basic(object):

    CONFIG = None

    def setUp(self):
        self.adapter = StandaloneTaskAdapter(deepcopy(self.CONFIG))

    def test_task_has_correct_name(self):
        data, kwargs = self.adapter.convert()
        self.assertEqual(data['name'], 'foobar-test-mytask')

    def test_task_has_correct_family(self):
        data, kwargs = self.adapter.convert()
        self.assertEqual(kwargs['task_definition'].data['family'], 'foobar-test-mytask')

    def test_family_set_to_name_if_no_family(self):
        config = deepcopy(self.CONFIG)
        del config['family']
        data, kwargs = StandaloneTaskAdapter(config).convert()
        self.assertEqual(kwargs['task_definition'].data['family'], 'foobar-test-mytask')

    def test_task_has_correct_network_mode(self):
        data, kwargs = self.adapter.convert()
        self.assertEqual(kwargs['task_definition'].data['networkMode'], 'bridge')
        config = deepcopy(self.CONFIG)
        config['network_mode'] = 'host'
        data, kwargs = StandaloneTaskAdapter(config).convert()
        self.assertEqual(kwargs['task_definition'].data['networkMode'], 'host')

    def test_task_has_correct_cluster(self):
        data, kwargs = self.adapter.convert()
        self.assertEqual(data['cluster'], 'foobar-cluster')

    def test_can_set_cluster(self):
        config = deepcopy(self.CONFIG)
        config['cluster'] = 'new-foobar-cluster'
        data, kwargs = StandaloneTaskAdapter(config).convert()
        self.assertEqual(data['cluster'], 'new-foobar-cluster')

    def test_can_set_task_cpu(self):
        config = deepcopy(self.CONFIG)
        config['cpu'] = 1024
        data, kwargs = StandaloneTaskAdapter(config).convert()
        self.assertEqual(kwargs['task_definition'].data['cpu'], '1024')

    def test_containers_have_correct_cpu(self):
        data, kwargs = self.adapter.convert()
        self.assertEqual(kwargs['task_definition'].containers[0].data['cpu'], 512)

    def test_can_set_task_memory(self):
        config = deepcopy(self.CONFIG)
        config['memory'] = 2048
        data, kwargs = StandaloneTaskAdapter(config).convert()
        self.assertEqual(kwargs['task_definition'].data['memory'], '2048')

    def test_containers_have_correct_memory(self):
        data, kwargs = self.adapter.convert()
        self.assertEqual(kwargs['task_definition'].containers[0].data['memory'], 512)

    def test_vpc_configuration_set_correctly(self):
        config = deepcopy(self.CONFIG)
        config['network_mode'] = 'awsvpc'
        config['vpc_configuration'] = {
            'subnets': ['subnet-1', 'subnet-2'],
            'security_groups': ['sg-1', 'sg-2'],
            'public_ip': 'DISABLED'
        }
        data, kwargs = StandaloneTaskAdapter(config).convert()
        self.assertEqual(
            data['networkConfiguration']['awsvpcConfiguration'],
            {
                'subnets': ['subnet-1', 'subnet-2'],
                'securityGroups': ['sg-1', 'sg-2'],
                'assignPublicIp': 'DISABLED'
            }
        )

    def test_network_mode_forced_to_awsvpc_if_we_have_vpc_configuration(self):
        """
        If we have vpc_configuration, our network mode should be forced to 'awsvpc'.
        """
        config = deepcopy(self.CONFIG)
        config['vpc_configuration'] = {
            'subnets': ['subnet-1', 'subnet-2'],
            'security_groups': ['sg-1', 'sg-2'],
            'public_ip': 'DISABLED'
        }
        data, kwargs = StandaloneTaskAdapter(config).convert()
        self.assertEqual(kwargs['task_definition'].data['networkMode'], 'awsvpc')

    def test_DEPLOYFISH_TASK_NAME_in_container_environment(self):
        data, kwargs = self.adapter.convert()
        self.assertTrue(
            {'name': 'DEPLOYFISH_TASK_NAME', 'value': 'foobar-test-mytask'} in
            kwargs['task_definition'].containers[0].data['environment'],
        )

    def test_DEPLOYFISH_ENVIRONMENT_set_correctly_in_container_environment(self):
        data, kwargs = self.adapter.convert()
        self.assertTrue(
            {'name': 'DEPLOYFISH_ENVIRONMENT', 'value': self.CONFIG['environment']} in
            kwargs['task_definition'].containers[0].data['environment'],
        )

    def test_DEPLOYFISH_CLUSTER_NAME_set_correctly_in_container_environment(self):
        data, kwargs = self.adapter.convert()
        self.assertTrue(
            {'name': 'DEPLOYFISH_CLUSTER_NAME', 'value': data['cluster']},
            kwargs['task_definition'].containers[0].data['environment'],
        )

    def test_secrets_are_set_properly_in_task_definition(self):
        data, kwargs = self.adapter.convert()
        td_secrets = kwargs['task_definition'].containers[0].data['secrets']
        self.assertEqual(len(td_secrets), len(self.CONFIG['config']))
        td_secrets_names = sorted([s['name'] for s in td_secrets])
        td_secrets_pks = sorted([s['valueFrom'] for s in td_secrets])
        source_names = sorted([s.split('=', 1)[0] for s in self.CONFIG['config']])
        source_pks = sorted(["{}.task-{}.{}".format(data['cluster'], data['name'], s) for s in source_names])
        self.assertEqual(td_secrets_names, source_names)
        self.assertEqual(td_secrets_pks, source_pks)


class TestStandaloneTaskAdapter_EC2(BaseTestStandaloneTaskAdapter_basic, unittest.TestCase):

    CONFIG = EC2_TASK_YML

    def test_launch_type_is_not_set(self):
        data, kwargs = self.adapter.convert()
        self.assertTrue('launch_type' not in data)


class TestStandaloneTaskAdapter_FARGATE(BaseTestStandaloneTaskAdapter_basic, unittest.TestCase):

    CONFIG = FARGATE_TASK_YML

    def test_launchType_is_set_to_FARGATE(self):
        data, kwargs = self.adapter.convert()
        self.assertTrue('launchType' in data)
        self.assertEqual(data['launchType'], 'FARGATE')

    def test_task_definition_has_requiredCompatibiliies_set_to_FARGATE(self):
        data, kwargs = self.adapter.convert()
        td = kwargs['task_definition']
        self.assertTrue('requiresCompatibilities' in td.data)
        self.assertEqual(td.data['requiresCompatibilities'], ['FARGATE'])

    def test_platformVersion_is_set_to_LATEST_if_not_provided(self):
        data, kwargs = self.adapter.convert()
        self.assertTrue('platformVersion' in data)
        self.assertEqual(data['platformVersion'], 'LATEST')

    def test_platformVersion_is_set_if_provided(self):
        config = deepcopy(self.CONFIG)
        config['platform_version'] = 'FOOBAR'
        data, kwargs = StandaloneTaskAdapter(config).convert()
        self.assertTrue('platformVersion' in data)
        self.assertEqual(data['platformVersion'], 'FOOBAR')


class TestStandaloneTaskAdapter_schedule_EC2(unittest.TestCase):

    CONFIG = deepcopy(EC2_TASK_YML)
    CONFIG['schedule'] = 'cron(5 * * * ? *)'
    CONFIG['schedule_role'] = 'MY_SCHEDULE_ROLE'

    def setUp(self):
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        cluster_data = {
            'clusterArn': 'MY_REAL_CLUSTER_ARN',
            'clusterName': 'foobar-cluster',
            'status': 'ACTIVE',
            'registeredContainerInstancesCount': 2,
            'runningTasksCount': 2,
            'pendingTasksCount': 0,
            'activeServicesCount': 1,
        }
        self.ClusterManager_get = Mock()
        self.ClusterManager_get.return_value = Cluster(cluster_data)

        self.adapter = StandaloneTaskAdapter(deepcopy(self.CONFIG))
        with Replacer() as r:
            r.replace('deployfish.core.models.ecs.ClusterManager.get', self.ClusterManager_get)
            self.data, self.kwargs = self.adapter.convert()

    def test_schedule_rule_is_returned(self):
        self.assertTrue('schedule' in self.kwargs)

    def test_schedule_rule_name_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].name, 'deployfish-foobar-test-mytask')

    def test_schedule_rule_ScheduleExpression_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].data['ScheduleExpression'], 'cron(5 * * * ? *)')

    def test_schedule_rule_cluster_arn_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].target.data['Arn'], 'MY_REAL_CLUSTER_ARN')

    def test_schedule_rule_RoleArn_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].target.data['RoleArn'], 'MY_SCHEDULE_ROLE')

    def test_schedule_rule_TaskCount_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].target.data['EcsParameters']['TaskCount'], 1)

    def test_schedule_rule_LaunchType_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].target.data['EcsParameters']['LaunchType'], 'EC2')

    def test_schedule_rule_Group_is_not_set(self):
        self.assertTrue('Group' not in self.kwargs['schedule'].target.data['EcsParameters'])

    def test_schedule_rule_NetworkConfiguration_is_not_set(self):
        self.assertTrue('NetworkConfiguration' not in self.kwargs['schedule'].target.data['EcsParameters'])


class TestStandaloneTaskAdapter_schedule_FARGATE(unittest.TestCase):

    CONFIG = deepcopy(FARGATE_TASK_YML)
    CONFIG['schedule'] = 'cron(5 * * * ? *)'
    CONFIG['schedule_role'] = 'MY_SCHEDULE_ROLE'
    CONFIG['vpc_configuration'] = {
        'subnets': ['subnet-1', 'subnet-2'],
        'security_groups': ['sg-1', 'sg-2'],
    }

    def setUp(self):
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        cluster_data = {
            'clusterArn': 'MY_REAL_CLUSTER_ARN',
            'clusterName': 'foobar-cluster',
            'status': 'ACTIVE',
            'registeredContainerInstancesCount': 2,
            'runningTasksCount': 2,
            'pendingTasksCount': 0,
            'activeServicesCount': 1,
        }
        self.ClusterManager_get = Mock()
        self.ClusterManager_get.return_value = Cluster(cluster_data)

        self.adapter = StandaloneTaskAdapter(deepcopy(self.CONFIG))
        with Replacer() as r:
            r.replace('deployfish.core.models.ecs.ClusterManager.get', self.ClusterManager_get)
            self.data, self.kwargs = self.adapter.convert()

    def test_schedule_rule_is_returned(self):
        self.assertTrue('schedule' in self.kwargs)

    def test_schedule_rule_name_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].name, 'deployfish-foobar-test-mytask')

    def test_schedule_rule_ScheduleExpression_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].data['ScheduleExpression'], 'cron(5 * * * ? *)')

    def test_schedule_rule_cluster_arn_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].target.data['Arn'], 'MY_REAL_CLUSTER_ARN')

    def test_schedule_rule_RoleArn_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].target.data['RoleArn'], 'MY_SCHEDULE_ROLE')

    def test_schedule_rule_TaskCount_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].target.data['EcsParameters']['TaskCount'], 1)

    def test_schedule_rule_LaunchType_is_correct(self):
        self.assertEqual(self.kwargs['schedule'].target.data['EcsParameters']['LaunchType'], 'FARGATE')

    def test_schedule_rule_Group_is_not_set(self):
        self.assertTrue('Group' not in self.kwargs['schedule'].target.data['EcsParameters'])

    def test_schedule_rule_NetworkConfiguration_is_set(self):
        self.assertTrue('NetworkConfiguration' in self.kwargs['schedule'].target.data['EcsParameters'])
        nc = self.kwargs['schedule'].target.data['EcsParameters']['NetworkConfiguration']['awsvpcConfiguration']
        self.assertEqual(nc['Subnets'], ['subnet-1', 'subnet-2'])
        self.assertEqual(nc['SecurityGroups'], ['sg-1', 'sg-2'])
