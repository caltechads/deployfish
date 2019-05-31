import unittest
from mock import Mock
from testfixtures import compare
from testfixtures import Replacer

import os

from deployfish.config import Config
from deployfish.aws.ecs import Service


class TestService_load_yaml_deploymenConfiguration_defaults(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fname = os.path.join(current_dir, 'simple.yml')
        config = Config(filename=fname, interpolate=False)
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


class TestService_load_yaml_deploymenConfiguration_defaults_from_aws(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fname = os.path.join(current_dir, 'simple.yml')
        config = Config(filename=fname, interpolate=False)
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
        fname = os.path.join(current_dir, 'simple.yml')
        config = Config(filename=fname, interpolate=False)
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
        fname = os.path.join(current_dir, 'simple.yml')
        config = Config(filename=fname, interpolate=False)
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
        compare(self.service.load_balancer, {
            'type': 'alb',
            'target_group_arn': 'my_target_group_arn',
            'container_name': 'example',
            'container_port': 443
        })

    def test_launchType(self):
        self.assertEqual(self.service.launchType, 'FARGATE')

    def test_vpc_configuration(self):
        compare(self.service.vpc_configuration, {
            'subnets': ['subnet-12345678', 'subnet-87654321'],
            'securityGroups': ['sg-12345678'],
            'assignPublicIp': 'ENABLED'
        })

    def test_placements(self):
        compare(self.service.placementConstraints, [
            {'type': 'distinctInstance'},
            {'type': 'memberOf', 'expression': 'attribute:ecs.instance-type =~ t2.*'}
        ])
        compare(self.service.placementStrategy, [
            {'type': 'random'},
            {'type': 'spread', 'field': 'attribute:ecs.availability-zone'}
        ])
