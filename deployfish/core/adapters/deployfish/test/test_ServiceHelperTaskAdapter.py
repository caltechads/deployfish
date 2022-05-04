from copy import deepcopy
import logging
import os
import unittest
from unittest.mock import Mock

from testfixtures import Replacer

from deployfish.exceptions import SchemaException  # noqa:F401
import deployfish.core.adapters  # noqa:F401
from deployfish.core.adapters import ServiceHelperTaskAdapter
from deployfish.core.models import Service, Cluster


logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)

SERVICE_YML = {
    'name': 'foobar-test',
    'cluster': 'foobar-cluster',
    'environment': 'test',
    'count': 1,
    'load_balancer': {
        'target_groups': [
            {
                'target_group_arn': 'MY_TARGET_GROUP_ARN',
                'container_name': 'foobar',
                'container_port': 8080
            }
        ]
    },
    'family': 'foobar-test',
    'network_mode': 'host',
    'task_role_arn': 'MY_TASK_ROLE_ARN',
    'execution_role': 'MY_EXECUTION_ROLE_ARN',
    'containers': [
        {
            'name': 'foobar',
            'image': 'foobar/foobar:0.1.0',
            'cpu': 512,
            'memory': 512,
            'ports': [
                '8080:8080'
            ],
            'environment': [
                'AWS_DEFAULT_REGION=us-west-2'
            ],
            'logging': {
                'driver': 'fluentd',
                'options': {
                    'fluentd-address': '127.0.0.1:24224',
                    'tag': 'foobar'
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


class BaseTestServiceHelperTaskAdapter_basic:

    TASKS = {
        'tasks': [
            {
                'family': 'foobar-tasks-test',
                'containers': [
                    {
                        'name': 'foobar',
                        'cpu': 1024,
                        'memory': 2048,
                    },
                ],
                'commands': [
                    {
                        'name': 'migrate',
                        'containers': [
                            {
                                'name': 'foobar',
                                'command': 'manage.py migrate'
                            }
                        ]
                    },
                    {
                        'name': 'update_index',
                        'containers': [
                            {
                                'name': 'foobar',
                                'command': 'manage.py update_index'
                            }
                        ]
                    },
                ]
            }
        ]
    }

    def setUp(self):
        self.service = Service.new(SERVICE_YML, 'deployfish')
        self.adapter = ServiceHelperTaskAdapter(deepcopy(self.TASKS), self.service)

    def test_correct_number_of_tasks_are_returned(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertEqual(len(data_list), 2)
        self.assertEqual(len(kwargs_list), 2)

    def test_tasks_have_correct_family(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertEqual(kwargs_list[0]['task_definition'].data['family'], 'foobar-tasks-test-migrate')
        self.assertEqual(kwargs_list[1]['task_definition'].data['family'], 'foobar-tasks-test-update-index')

    def test_tasks_have_appropriate_family_set_if_not_supplied(self):
        tasks_yml = deepcopy(self.TASKS)
        del tasks_yml['tasks'][0]['family']
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertEqual(kwargs_list[0]['task_definition'].data['family'], 'foobar-test-tasks-migrate')
        self.assertEqual(kwargs_list[1]['task_definition'].data['family'], 'foobar-test-tasks-update-index')

    def test_tasks_have_correct_network_mode(self):
        """
        If we have no vpc_configuration, our network mode should be forced to 'bridge'.
        """
        data_list, kwargs_list = self.adapter.convert()
        self.assertEqual(kwargs_list[0]['task_definition'].data['networkMode'], 'bridge')
        self.assertEqual(kwargs_list[1]['task_definition'].data['networkMode'], 'bridge')

    def test_containers_should_have_no_ports(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertTrue('portMappings' not in kwargs_list[0]['task_definition'].containers[0].data)
        self.assertTrue('portMappings' not in kwargs_list[1]['task_definition'].containers[0].data)

    def test_task_containers_have_correct_command(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertEqual(
            kwargs_list[0]['task_definition'].containers[0].data['command'],
            ['manage.py', 'migrate']
        )
        self.assertEqual(
            kwargs_list[1]['task_definition'].containers[0].data['command'],
            ['manage.py', 'update_index']
        )

    def test_commands_have_correct_names(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertEqual(data_list[0]['name'], 'migrate')
        self.assertEqual(data_list[1]['name'], 'update_index')

    def test_commands_have_correct_cluster(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertEqual(data_list[0]['cluster'], 'foobar-cluster')
        self.assertEqual(data_list[1]['cluster'], 'foobar-cluster')

    def test_can_set_cluster(self):
        tasks_yml = deepcopy(self.TASKS)
        tasks_yml['tasks'][0]['cluster'] = 'new-foobar-cluster'
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertEqual(data_list[0]['cluster'], 'new-foobar-cluster')
        self.assertEqual(data_list[1]['cluster'], 'new-foobar-cluster')

    def test_can_set_per_container_cluster(self):
        tasks_yml = deepcopy(self.TASKS)
        tasks_yml['tasks'][0]['commands'][0]['cluster'] = 'new-foobar-cluster'
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertEqual(data_list[0]['cluster'], 'new-foobar-cluster')
        self.assertEqual(data_list[1]['cluster'], 'foobar-cluster')

    def test_can_set_task_cpu(self):
        tasks_yml = deepcopy(self.TASKS)
        tasks_yml['tasks'][0]['cpu'] = 1024
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertEqual(kwargs_list[0]['task_definition'].data['cpu'], '1024')
        self.assertEqual(kwargs_list[1]['task_definition'].data['cpu'], '1024')

    def test_containers_have_correct_cpu(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertEqual(kwargs_list[0]['task_definition'].containers[0].data['cpu'], 1024)
        self.assertEqual(kwargs_list[1]['task_definition'].containers[0].data['cpu'], 1024)

    def test_commands_can_have_their_own_cpu(self):
        tasks_yml = deepcopy(self.TASKS)
        tasks_yml['tasks'][0]['commands'][0]['containers'][0]['cpu'] = 512
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertEqual(kwargs_list[0]['task_definition'].containers[0].data['cpu'], 512)
        self.assertEqual(kwargs_list[1]['task_definition'].containers[0].data['cpu'], 1024)

    def test_containers_cpu_defaults_to_service(self):
        tasks_yml = deepcopy(self.TASKS)
        del tasks_yml['tasks'][0]['containers'][0]['cpu']
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertEqual(kwargs_list[0]['task_definition'].containers[0].data['cpu'], 512)
        self.assertEqual(kwargs_list[1]['task_definition'].containers[0].data['cpu'], 512)

    def test_can_set_task_memory(self):
        tasks_yml = deepcopy(self.TASKS)
        tasks_yml['tasks'][0]['memory'] = 2048
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertEqual(kwargs_list[0]['task_definition'].data['memory'], '2048')
        self.assertEqual(kwargs_list[1]['task_definition'].data['memory'], '2048')

    def test_containers_have_correct_memory(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertEqual(kwargs_list[0]['task_definition'].containers[0].data['memory'], 2048)
        self.assertEqual(kwargs_list[1]['task_definition'].containers[0].data['memory'], 2048)

    def test_commands_can_have_their_own_memory(self):
        tasks_yml = deepcopy(self.TASKS)
        tasks_yml['tasks'][0]['commands'][0]['containers'][0]['memory'] = 512
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertEqual(kwargs_list[0]['task_definition'].containers[0].data['memory'], 512)
        self.assertEqual(kwargs_list[1]['task_definition'].containers[0].data['memory'], 2048)

    def test_containers_memory_defaults_to_service(self):
        tasks_yml = deepcopy(self.TASKS)
        del tasks_yml['tasks'][0]['containers'][0]['memory']
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertEqual(kwargs_list[0]['task_definition'].containers[0].data['memory'], 512)
        self.assertEqual(kwargs_list[1]['task_definition'].containers[0].data['memory'], 512)

    def test_DEPLOYFISH_SERVICE_NAME_not_in_container_environment(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertFalse(
            {'name': 'DEPLOYFISH_SERVICE_NAME', 'value': 'foobar-test'} in
            kwargs_list[0]['task_definition'].containers[0].data['environment'],
        )
        self.assertFalse(
            {'name': 'DEPLOYFISH_SERVICE_NAME', 'value': 'foobar-test'} in
            kwargs_list[1]['task_definition'].containers[0].data['environment'],
        )

    def test_DEPLOYFISH_TASK_NAME_in_container_environment(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertTrue(
            {'name': 'DEPLOYFISH_TASK_NAME', 'value': 'foobar-tasks-test-migrate'} in
            kwargs_list[0]['task_definition'].containers[0].data['environment'],
        )
        self.assertTrue(
            {'name': 'DEPLOYFISH_TASK_NAME', 'value': 'foobar-tasks-test-update-index'} in
            kwargs_list[1]['task_definition'].containers[0].data['environment'],
        )

    def test_DEPLOYFISH_ENVIRONMENT_set_correctly_in_container_environment(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertTrue(
            {'name': 'DEPLOYFISH_ENVIRONMENT', 'value': self.service.deployfish_environment} in
            kwargs_list[0]['task_definition'].containers[0].data['environment'],
        )
        self.assertTrue(
            {'name': 'DEPLOYFISH_ENVIRONMENT', 'value': self.service.deployfish_environment} in
            kwargs_list[1]['task_definition'].containers[0].data['environment'],
        )

    def test_DEPLOYFISH_CLUSTER_NAME_set_correctly_in_container_environment(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertTrue(
            {'name': 'DEPLOYFISH_CLUSTER_NAME', 'value': data_list[0]['cluster']},
            kwargs_list[0]['task_definition'].containers[0].data['environment'],
        )
        self.assertTrue(
            {'name': 'DEPLOYFISH_CLUSTER_NAME', 'value': data_list[1]['cluster']},
            kwargs_list[1]['task_definition'].containers[0].data['environment'],
        )

    def test_old_style_command_definition_works(self):
        """
        Ensure old style command definitions still work:

            tasks:
              - family: foobar-test-helper
                environment: test
                network_mode: bridge
                task_role_arn: ${terraform.iam_task_role}
                containers:
                - name: foobar
                  image: ${terraform.ecr_repo_url}:0.1.0
                  cpu: 128
                  memory: 384
                  commands:
                    migrate: ./manage.py migrate
                    update_index: ./manage.py update_index
        """
        tasks_yml = deepcopy(self.TASKS)
        tasks_yml['tasks'][0]['containers'][0]['commands'] = {
            'migrate': "manage.py migrate",
            'update_index': 'manage.py update_index'
        }
        del tasks_yml['tasks'][0]['commands']
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertEqual(
            kwargs_list[0]['task_definition'].containers[0].data['command'],
            ['manage.py', 'migrate']
        )
        self.assertEqual(
            kwargs_list[1]['task_definition'].containers[0].data['command'],
            ['manage.py', 'update_index']
        )


class TestServiceHelperTaskAdapter_EC2(BaseTestServiceHelperTaskAdapter_basic, unittest.TestCase):

    def test_launch_type_is_not_set(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertTrue('launch_type' not in data_list[0])
        self.assertTrue('launch_type' not in data_list[1])


class TestServiceHelperTaskAdapter_FARGATE(BaseTestServiceHelperTaskAdapter_basic, unittest.TestCase):

    TASKS = {
        'tasks': [
            {
                'family': 'foobar-tasks-test',
                'launch_type': 'FARGATE',
                'vpc_configuration': {
                    'subnets': ['subnet-1', 'subnet-2'],
                    'security_groups': ['sg-1', 'sg-2'],
                    'public_ip': 'ENABLED'
                },
                'containers': [
                    {
                        'name': 'foobar',
                        'cpu': 1024,
                        'memory': 2048,
                    },
                ],
                'commands': [
                    {
                        'name': 'migrate',
                        'containers': [
                            {
                                'name': 'foobar',
                                'command': 'manage.py migrate',
                            }
                        ]
                    },
                    {
                        'name': 'update_index',
                        'containers': [
                            {
                                'name': 'foobar',
                                'command': 'manage.py update_index'
                            }
                        ]
                    },
                ]
            }
        ]
    }

    def test_can_set_task_memory(self):
        tasks_yml = deepcopy(self.TASKS)
        tasks_yml['tasks'][0]['memory'] = 2048
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertEqual(kwargs_list[0]['task_definition'].data['memory'], '2048')
        self.assertEqual(kwargs_list[1]['task_definition'].data['memory'], '2048')

    def test_launchType_is_set_to_FARGATE(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertTrue('launchType' in data_list[0])
        self.assertEqual(data_list[0]['launchType'], 'FARGATE')
        self.assertTrue('launchType' in data_list[1])
        self.assertEqual(data_list[1]['launchType'], 'FARGATE')

    def test_task_definition_has_requiredCompatibiliies_set_to_FARGATE(self):
        data_list, kwargs_list = self.adapter.convert()
        for kwargs in kwargs_list:
            td = kwargs['task_definition']
            self.assertTrue('requiresCompatibilities' in td.data)
            self.assertEqual(td.data['requiresCompatibilities'], ['FARGATE'])

    def test_platformVersion_is_set_to_LATEST_if_not_provided(self):
        data_list, kwargs_list = self.adapter.convert()
        self.assertTrue('platformVersion' in data_list[0])
        self.assertEqual(data_list[0]['platformVersion'], 'LATEST')
        self.assertTrue('platformVersion' in data_list[1])
        self.assertEqual(data_list[1]['platformVersion'], 'LATEST')

    def test_platformVersion_is_set_if_provided(self):
        tasks_yml = deepcopy(self.TASKS)
        tasks_yml['tasks'][0]['platform_version'] = 'FOOBAR'
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        self.assertTrue('platformVersion' in data_list[0])
        self.assertEqual(data_list[0]['platformVersion'], 'FOOBAR')
        self.assertTrue('platformVersion' in data_list[1])
        self.assertEqual(data_list[1]['platformVersion'], 'FOOBAR')

    def test_tasks_have_correct_network_mode(self):
        """
        If we have vpc_configuration, our network mode should be forced to 'awsvpc'.
        """
        data_list, kwargs_list = self.adapter.convert()
        self.assertEqual(kwargs_list[0]['task_definition'].data['networkMode'], 'awsvpc')
        self.assertEqual(kwargs_list[1]['task_definition'].data['networkMode'], 'awsvpc')

    def test_tasks_have_vpc_configuration(self):
        data_list, kwargs_list = self.adapter.convert()
        for data in data_list:
            self.assertTrue('networkConfiguration' in data)
            self.assertTrue('awsvpcConfiguration' in data['networkConfiguration'])
            self.assertEqual(
                data['networkConfiguration']['awsvpcConfiguration'],
                {
                    'subnets': ['subnet-1', 'subnet-2'],
                    'securityGroups': ['sg-1', 'sg-2'],
                    'assignPublicIp': 'ENABLED'
                }
            )

    def test_commands_can_have_their_own_vpc_configuration(self):
        tasks_yml = deepcopy(self.TASKS)
        vpc_info = deepcopy(tasks_yml['tasks'][0]['vpc_configuration'])
        del tasks_yml['tasks'][0]['vpc_configuration']
        del tasks_yml['tasks'][0]['launch_type']
        tasks_yml['tasks'][0]['commands'][0]['vpc_configuration'] = vpc_info
        tasks_yml['tasks'][0]['commands'][0]['launch_type'] = 'FARGATE'
        data_list, kwargs_list = ServiceHelperTaskAdapter(tasks_yml, self.service).convert()
        # command 0 should be configured for FARGATE
        self.assertEqual(data_list[0]['launchType'], 'FARGATE')
        self.assertEqual(data_list[0]['platformVersion'], 'LATEST')
        self.assertTrue('networkConfiguration' in data_list[0])
        self.assertTrue('awsvpcConfiguration' in data_list[0]['networkConfiguration'])
        self.assertEqual(
            data_list[0]['networkConfiguration']['awsvpcConfiguration'],
            {
                'subnets': ['subnet-1', 'subnet-2'],
                'securityGroups': ['sg-1', 'sg-2'],
                'assignPublicIp': 'ENABLED'
            }
        )
        self.assertEqual(kwargs_list[0]['task_definition'].data['requiresCompatibilities'], ['FARGATE'])
        # command 1 should not be configured for FARGATE
        self.assertTrue('networkConfiguration' not in data_list[1])
        self.assertEqual(data_list[1]['launchType'], 'EC2')
        self.assertTrue('platformVersion' not in data_list[1])
        self.assertEqual(kwargs_list[1]['task_definition'].data['requiresCompatibilities'], ['EC2'])


class TestServiceHelperTaskAdapter_schedule_EC2(unittest.TestCase):

    TASKS = {
        'tasks': [
            {
                'family': 'foobar-tasks-test',
                'containers': [
                    {
                        'name': 'foobar',
                        'cpu': 1024,
                        'memory': 2048,
                    },
                ],
                'commands': [
                    {
                        'name': 'migrate',
                        'schedule': 'cron(5 * * * ? *)',
                        'schedule_role': 'MY_SCHEDULE_ROLE',
                        'containers': [
                            {
                                'name': 'foobar',
                                'command': 'manage.py migrate'
                            }
                        ]
                    }
                ]
            }
        ]
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

        self.service = Service.new(SERVICE_YML, 'deployfish')
        self.adapter = ServiceHelperTaskAdapter(deepcopy(self.TASKS), self.service)
        with Replacer() as r:
            r.replace('deployfish.core.models.ecs.ClusterManager.get', self.ClusterManager_get)
            self.data_list, self.kwargs_list = self.adapter.convert()

    def test_schedule_rule_is_returned(self):
        self.assertTrue('schedule' in self.kwargs_list[0])

    def test_schedule_rule_name_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].name, 'deployfish-foobar-tasks-test-migrate')

    def test_schedule_rule_ScheduleExpression_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].data['ScheduleExpression'], 'cron(5 * * * ? *)')

    def test_schedule_rule_cluster_arn_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].target.data['Arn'], 'MY_REAL_CLUSTER_ARN')

    def test_schedule_rule_RoleArn_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].target.data['RoleArn'], 'MY_SCHEDULE_ROLE')

    def test_schedule_rule_TaskCount_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].target.data['EcsParameters']['TaskCount'], 1)

    def test_schedule_rule_LaunchType_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].target.data['EcsParameters']['LaunchType'], 'EC2')

    def test_schedule_rule_Group_is_not_set(self):
        self.assertTrue('Group' not in self.kwargs_list[0]['schedule'].target.data['EcsParameters'])

    def test_schedule_rule_NetworkConfiguration_is_not_set(self):
        self.assertTrue('NetworkConfiguration' not in self.kwargs_list[0]['schedule'].target.data['EcsParameters'])


class TestServiceHelperTaskAdapter_schedule_FARGATE(unittest.TestCase):

    TASKS = {
        'tasks': [
            {
                'family': 'foobar-tasks-test',
                'launch_type': 'FARGATE',
                'vpc_configuration': {
                    'subnets': ['subnet-1', 'subnet-2'],
                    'security_groups': ['sg-1', 'sg-2'],
                    'public_ip': True
                },
                'containers': [
                    {
                        'name': 'foobar',
                        'cpu': 1024,
                        'memory': 2048,
                    },
                ],
                'commands': [
                    {
                        'name': 'migrate',
                        'schedule': 'cron(5 * * * ? *)',
                        'schedule_role': 'MY_SCHEDULE_ROLE',
                        'containers': [
                            {
                                'name': 'foobar',
                                'command': 'manage.py migrate'
                            }
                        ]
                    }
                ]
            }
        ]
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

        self.service = Service.new(SERVICE_YML, 'deployfish')
        self.adapter = ServiceHelperTaskAdapter(deepcopy(self.TASKS), self.service)
        with Replacer() as r:
            r.replace('deployfish.core.models.ecs.ClusterManager.get', self.ClusterManager_get)
            self.data_list, self.kwargs_list = self.adapter.convert()

    def test_schedule_rule_is_returned(self):
        self.assertTrue('schedule' in self.kwargs_list[0])

    def test_schedule_rule_name_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].name, 'deployfish-foobar-tasks-test-migrate')

    def test_schedule_rule_ScheduleExpression_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].data['ScheduleExpression'], 'cron(5 * * * ? *)')

    def test_schedule_rule_cluster_arn_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].target.data['Arn'], 'MY_REAL_CLUSTER_ARN')

    def test_schedule_rule_RoleArn_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].target.data['RoleArn'], 'MY_SCHEDULE_ROLE')

    def test_schedule_rule_TaskCount_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].target.data['EcsParameters']['TaskCount'], 1)

    def test_schedule_rule_LaunchType_is_correct(self):
        self.assertEqual(self.kwargs_list[0]['schedule'].target.data['EcsParameters']['LaunchType'], 'FARGATE')

    def test_schedule_rule_Group_is_not_set(self):
        self.assertTrue('Group' not in self.kwargs_list[0]['schedule'].target.data['EcsParameters'])

    def test_schedule_rule_NetworkConfiguration_is_set(self):
        self.assertTrue('NetworkConfiguration' in self.kwargs_list[0]['schedule'].target.data['EcsParameters'])
        nc = self.kwargs_list[0]['schedule'].target.data['EcsParameters']['NetworkConfiguration']['awsvpcConfiguration']
        self.assertEqual(nc['Subnets'], ['subnet-1', 'subnet-2'])
        self.assertEqual(nc['SecurityGroups'], ['sg-1', 'sg-2'])
