import os
import unittest
from mock import Mock
from testfixtures import compare
from testfixtures import Replacer

from deployfish.config import Config
from deployfish.aws.ecs import Service
from deployfish.aws.systems_manager import Parameter


class TestService_load_yaml_deploymentConfiguration_defaults(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        config = Config(filename=filename, interpolate=False)
        del config.raw['services'][0]['maximum_percent']
        del config.raw['services'][0]['minimum_healthy_percent']
        with Replacer() as r:
            r.replace('deployfish.aws.ecs.Service.from_aws', Mock())
            self.service = Service('foobar-prod', config=config)

    def test_maximum_percent(self):
        self.assertEqual(self.service.maximumPercent, 200)

    def test_minimum_healthy_percent(self):
        self.assertEqual(self.service.minimumHealthyPercent, 0)

    def test_placements(self):
        self.assertEqual(self.service.placementConstraints, [])
        self.assertEqual(self.service.placementStrategy, [])

    def test_scheduling_strategy(self):
        self.assertEqual(self.service.schedulingStrategy, 'REPLICA')

    def test_load_balancer_render(self):
        r = self.service._render('foobar-prod:1')
        self.assertTrue('loadBalancers' in r)
        compare(
            r['loadBalancers'],
            [
                {
                    'loadBalancerName': 'foobar-prod',
                    'containerName': 'example',
                    'containerPort': 443
                }
            ]
        )


class TestService_load_yaml_deploymentConfiguration_defaults_from_aws(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        config = Config(filename=filename, interpolate=False)
        del config.raw['services'][0]['maximum_percent']
        del config.raw['services'][0]['minimum_healthy_percent']
        with Replacer() as r:
            r.replace('deployfish.aws.ecs.Service.from_aws', Mock())
            self.service = Service('foobar-prod', config=config)
            # This is ugly, but it was the only way I could figure out to
            # simulate the AWS load
            self.service._Service__aws_service = {
                'deploymentConfiguration': {
                    'minimumHealthyPercent': 53,
                    'maximumPercent': 275
                },
                'placementConstraints': [{
                    'type': 'memberOf',
                    'expression': 'attribute:ecs.instance-type =~ t2.*'
                }],
                'placementStrategy': [{
                    'type': 'binpack',
                    'field': 'memory'
                }],
                'networkConfiguration': {
                    'awsvpcConfiguration': {
                        'subnets': ['subnet-12345678'],
                        'security_groups': ['sg-12345678'],
                        'assignPublicIp': 'DISABLED'
                    }
                }
            }

    def test_maximum_percent(self):
        self.assertEqual(self.service.maximumPercent, 275)

    def test_minimum_healthy_percent(self):
        self.assertEqual(self.service.minimumHealthyPercent, 53)

    def test_placements(self):
        compare(self.service.placementConstraints, [{
            'type': 'memberOf',
            'expression': 'attribute:ecs.instance-type =~ t2.*'
        }])
        compare(self.service.placementStrategy, [{
            'type': 'binpack',
            'field': 'memory'
        }])
        compare(self.service.vpc_configuration, {
            'subnets': ['subnet-12345678'],
            'security_groups': ['sg-12345678'],
            'assignPublicIp': 'DISABLED'
        })


class TestService_load_yaml(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        config = Config(filename=filename, interpolate=False)
        with Replacer() as r:
            r.replace('deployfish.aws.ecs.Service.from_aws', Mock())
            self.service = Service('foobar-prod', config=config)

    def test_serviceName(self):
        self.assertEqual(self.service.serviceName, 'foobar-prod')

    def test_clusterName(self):
        self.assertEqual(self.service.clusterName, 'foobar-prod')

    def test_roleArn(self):
        self.assertEqual(self.service.roleArn, 'a_task_role_arn')

    def test_count(self):
        self.assertEqual(self.service.count, 2)

    def test_maximum_percent(self):
        self.assertEqual(self.service.maximumPercent, 250)

    def test_minimum_healthy_percent(self):
        self.assertEqual(self.service.minimumHealthyPercent, 50)

    def test_load_balancer(self):
        compare(self.service.load_balancer, {
            'type': 'elb',
            'load_balancer_name': 'foobar-prod',
            'container_name': 'example',
            'container_port': 443
        })


class TestService_load_yaml_alternate(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        config = Config(filename=filename, interpolate=False)
        with Replacer() as r:
            r.replace('deployfish.aws.ecs.Service.from_aws', Mock())
            self.service = Service('foobar-prod2', config=config)

    def test_serviceName(self):
        self.assertEqual(self.service.serviceName, 'foobar-prod2')

    def test_clusterName(self):
        self.assertEqual(self.service.clusterName, 'foobar-prod2')

    def test_roleArn(self):
        self.assertEqual(self.service.roleArn, 'a_task_role_arn')

    def test_count(self):
        self.assertEqual(self.service.count, 2)

    def test_maximum_percent(self):
        self.assertEqual(self.service.maximumPercent, 250)

    def test_minimum_healthy_percent(self):
        self.assertEqual(self.service.minimumHealthyPercent, 50)

    def test_load_balancer(self):
        compare(self.service.load_balancer, [{
            'type': 'alb',
            'target_group_arn': 'my_target_group_arn',
            'container_name': 'example',
            'container_port': 443
        }])

    def test_launchType(self):
        self.assertEqual(self.service.launchType, 'FARGATE')

    def test_vpc_configuration(self):
        compare(self.service.vpc_configuration, {
            'subnets': ['subnet-12345678', 'subnet-87654321'],
            'securityGroups': ['sg-12345678'],
            'assignPublicIp': 'ENABLED'
        })

    def test_vpc_configuration_render(self):
        r = self.service._render('foobar-prod2:1')
        self.assertTrue('networkConfiguration' in r)
        self.assertTrue('awsvpcConfiguration' in r['networkConfiguration'])
        compare(
            r['networkConfiguration']['awsvpcConfiguration'],
            {
                'subnets': ['subnet-12345678', 'subnet-87654321'],
                'securityGroups': ['sg-12345678'],
                'assignPublicIp': 'ENABLED'
            }
        )

    def test_placements(self):
        compare(self.service.placementConstraints, [
            {'type': 'distinctInstance'},
            {'type': 'memberOf', 'expression': 'attribute:ecs.instance-type =~ t2.*'}
        ])
        compare(self.service.placementStrategy, [
            {'type': 'random'},
            {'type': 'spread', 'field': 'attribute:ecs.availability-zone'}
        ])

    def test_load_balancer_render(self):
        r = self.service._render('foobar-prod2:1')
        self.assertTrue('loadBalancers' in r)
        compare(
            r['loadBalancers'],
            [
                {
                    'targetGroupArn': 'my_target_group_arn',
                    'containerName': 'example',
                    'containerPort': 443
                }
            ]
        )

    def test_capacity_provider_strategy(self):
        compare(
            self.service.capacity_provider_strategy,
            [
                {'provider': 'foobar-cap-provider', 'weight': 1, 'base': 1},
                {'provider': 'foobar-cap-provider2', 'weight': 2}
            ]
        )

    def test_capacity_provider_strategy_render(self):
        r = self.service._render('foobar-prod2:1')
        self.assertTrue('capacityProviderStrategy' in r)
        compare(
            r['capacityProviderStrategy'],
            [
                {'capacityProvider': 'foobar-cap-provider', 'weight': 1, 'base': 1},
                {'capacityProvider': 'foobar-cap-provider2', 'weight': 2}
            ]
        )


class TestService_load_yaml_multiple_target_groups(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        config = Config(filename=filename, interpolate=False)
        with Replacer() as r:
            r.replace('deployfish.aws.ecs.Service.from_aws', Mock())
            self.service = Service('foobar-prod3', config=config)

    def test_serviceName(self):
        self.assertEqual(self.service.serviceName, 'foobar-prod3')

    def test_clusterName(self):
        self.assertEqual(self.service.clusterName, 'foobar-prod3')

    def test_load_balancer(self):
        compare(
            self.service.load_balancer,
            [
                {
                    'type': 'alb',
                    'target_group_arn': 'my_target_group_arn_443',
                    'container_name': 'example',
                    'container_port': 443
                },
                {
                    'type': 'alb',
                    'target_group_arn': 'my_target_group_arn_80',
                    'container_name': 'example',
                    'container_port': 80
                }
            ]
        )

    def test_load_balancer_render(self):
        r = self.service._render('foobar-prod3:1')
        self.assertTrue('loadBalancers' in r)
        compare(
            r['loadBalancers'],
            [
                {
                    'targetGroupArn': 'my_target_group_arn_443',
                    'containerName': 'example',
                    'containerPort': 443
                },
                {
                    'targetGroupArn': 'my_target_group_arn_80',
                    'containerName': 'example',
                    'containerPort': 80
                }
            ]
        )


class TestService_load_yaml_multiple_target_groups_from_aws(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        config = Config(filename=filename, interpolate=False)
        with Replacer() as r:
            r.replace('deployfish.aws.ecs.Service.from_aws', Mock())
            self.service = Service('foobar-prod3', config=config)
            self.service._Service__aws_service = {
                'loadBalancers': [
                    {
                        'targetGroupArn': 'my_target_group_arn_8443',
                        'containerName': 'example',
                        'containerPort': 8443
                    },
                    {
                        'targetGroupArn': 'my_target_group_arn_8080',
                        'containerName': 'example',
                        'containerPort': 8080
                    }
                ]
            }

    def test_load_balancer(self):
        compare(
            self.service.load_balancer,
            [
                {
                    'type': 'alb',
                    'target_group_arn': 'my_target_group_arn_8443',
                    'container_name': 'example',
                    'container_port': 8443
                },
                {
                    'type': 'alb',
                    'target_group_arn': 'my_target_group_arn_8080',
                    'container_name': 'example',
                    'container_port': 8080
                }
            ]
        )


class TestService_load_yaml_capacity_provider_strategy_from_aws(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        config = Config(filename=filename, interpolate=False)
        with Replacer() as r:
            r.replace('deployfish.aws.ecs.Service.from_aws', Mock())
            self.service = Service('foobar-prod2', config=config)
            self.service._Service__aws_service = {
                'capacityProviderStrategy': [
                    {
                        'capacityProvider': 'foobar-cap-1',
                        'weight': 1,
                        'base': 1
                    }
                ]
            }

    def test_capacity_provider_strategy(self):
        compare(
            self.service.capacity_provider_strategy,
            [
                {'provider': 'foobar-cap-1', 'weight': 1, 'base': 1}
            ]
        )


class TestService_embedded_config(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        self.config = Config(filename=filename, interpolate=False)
        with Replacer() as r:
            r.replace('deployfish.aws.ecs.Service.from_aws', Mock())
            self.service = Service('foobar-prod2', config=self.config)
            p = Parameter('foobar-service', 'foobar-cluster', yml='KEY=VALUE')
            self.service.parameter_store.append(p)
            self.service.desired_task_definition.set_parameter_store(self.service.parameter_store)

    def test_config_with_execution_role(self):
        self.assertEqual(len(self.service.desired_task_definition.containers[0].secrets), 1)


class TestService_no_embedded_config(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        self.config = Config(filename=filename, interpolate=False)
        with Replacer() as r:
            r.replace('deployfish.aws.ecs.Service.from_aws', Mock())
            self.service = Service('foobar-prod', config=self.config)
            p = Parameter('foobar-service', 'foobar-cluster', yml='KEY=VALUE')
            self.service.parameter_store.append(p)
            self.service.desired_task_definition.set_parameter_store(self.service.parameter_store)

    def test_ignore_config_when_no_execution_role(self):
        self.assertEqual(len(self.service.desired_task_definition.containers[0].secrets), 0)


class TestService_ec2_secrets_in_task_definition(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        self.config = Config(filename=filename, interpolate=False)
        client_mock = Mock()
        client_mock.get_parameters.return_value = {'Parameters': []}
        client_mock.describe_parameters.return_value = {'Parameters': []}
        session_mock = Mock(client=Mock(return_value=client_mock))
        with Replacer() as r:
            r.replace('deployfish.aws.ecs.Service.from_aws', Mock())
            r.replace('deployfish.aws.ecs.TaskDefinition.create', Mock())
            r.replace('deployfish.aws.boto3_session', session_mock)
            self.service = Service('foobar-secrets-ec2', config=self.config)
            self.service.create()

    def test_sanity_check_name(self):
        self.assertEqual(self.service.serviceName, 'foobar-secrets-ec2')

    def test_sanity_check_config(self):
        self.assertEqual(len(self.config.get_service('foobar-secrets-ec2')['config']), 3)

    def test_config_with_execution_role(self):
        self.assertEqual(len(self.service.desired_task_definition.containers[0].secrets), 3)
        self.assertEqual(self.service.desired_task_definition.containers[0].secrets[0].name, 'VAR1')
        self.assertEqual(self.service.desired_task_definition.containers[0].secrets[1].name, 'VAR2')


class TestService_no_ec2_secrets_in_task_definition_if_no_execution_role(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        self.config = Config(filename=filename, interpolate=False)
        del self.config.raw['services'][4]['execution_role']
        client_mock = Mock()
        client_mock.get_parameters.return_value = {'Parameters': []}
        client_mock.describe_parameters.return_value = {'Parameters': []}
        session_mock = Mock(client=Mock(return_value=client_mock))
        with Replacer() as r:
            r.replace('deployfish.aws.ecs.Service.from_aws', Mock())
            r.replace('deployfish.aws.ecs.TaskDefinition.create', Mock())
            r.replace('deployfish.aws.boto3_session', session_mock)
            self.service = Service('foobar-secrets-ec2', config=self.config)
            self.service.create()

    def test_sanity_check_name(self):
        self.assertEqual(self.service.serviceName, 'foobar-secrets-ec2')

    def test_sanity_check_config(self):
        self.assertEqual(len(self.config.get_service('foobar-secrets-ec2')['config']), 3)

    def test_config_with_execution_role(self):
        self.assertEqual(len(self.service.desired_task_definition.containers[0].secrets), 0)
