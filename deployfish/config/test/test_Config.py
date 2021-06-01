import json
import os
import pprint
import unittest
from mock import Mock, call
from testfixtures import Replacer

from deployfish.config.config import Config


def statefile_loader(state_file_url, profile=None, region=None):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if state_file_url == 's3://my-qa-statefile':
        with open(os.path.join(current_dir, 'terraform.tfstate.qa')) as f:
            return json.loads(f.read())
    elif state_file_url == 's3://my-prod-statefile':
        with open(os.path.join(current_dir, 'terraform.tfstate.prod')) as f:
            return json.loads(f.read())


class TestContainerDefinition_terraform_statefile_interpolation(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_yml = os.path.join(current_dir, 'terraform_interpolate.yml')
        with Replacer() as r:
            self.get_mock = r('deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3', Mock())
            self.get_mock.side_effect = statefile_loader
            self.config = Config.new(filename=config_yml)

    def test_environment_gets_replaced_for_each_environment(self):
        calls = [
            call('s3://my-qa-statefile', profile=None, region=None),
            call('s3://my-prod-statefile', profile=None, region=None),
        ]
        self.get_mock.assert_has_calls(calls)

    def test_file_interpolation_gets_values_from_correct_statefile(self):
        prod = self.config.get_section_item('services', 'foobar-prod')
        self.assertEqual(prod['cluster'], 'foobar-cluster-prod')
        self.assertEqual(prod['load_balancer']['load_balancer_name'], 'foobar-prod-elb')
        self.assertEqual(prod['task_role_arn'], 'arn:aws:iam::324958023459:role/foobar-prod-task')
        qa = self.config.get_section_item('services', 'foobar-qa')
        self.assertEqual(qa['cluster'], 'foobar-cluster-qa')
        self.assertEqual(qa['load_balancer']['load_balancer_name'], 'foobar-qa-elb')
        self.assertEqual(qa['task_role_arn'], 'arn:aws:iam::324958023459:role/foobar-qa-task')


class TestContainerDefinition_load_yaml(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        state_file = os.path.join(current_dir, 'terraform.tfstate')
        config_yml = os.path.join(current_dir, 'interpolate.yml')
        env_file = os.path.join(current_dir, 'env_file.env')
        with open(state_file) as f:
            tfstate = json.loads(f.read())
        with Replacer() as r:
            get_mock = r('deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3', Mock())
            get_mock.return_value = tfstate
            self.config = Config.new(filename=config_yml, env_file=env_file)

    def test_terraform_simple_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['cluster'], 'foobar-cluster-prod')

    def test_terraform_nested_dict_interpolation(self):
        self.assertEqual(
            self.config.get_service('foobar-prod')['load_balancer']['load_balancer_name'],
            'foobar-elb-prod'
        )

    def test_terraform_nested_list_interpolation(self):
        self.assertEqual(
            self.config.get_service('foobar-prod')['containers'][0]['environment'][2],
            'SECRETS_BUCKET_NAME=my-config-store'
        )

    def test_terraform_list_output_interpolation(self):
        self.assertListEqual(
            self.config.get_service('foobar-prod')['vpc_configuration']['security_groups'],
            ['sg-1234567', 'sg-2345678', 'sg-3456789']
        )

    def test_terraform_map_output_interpolation(self):
        self.assertListEqual(
            self.config.get_service('output-test')['vpc_configuration']['subnets'],
            ['subnet-1234567']
        )
        self.assertListEqual(
            self.config.get_service('output-test')['vpc_configuration']['security_groups'],
            ['sg-1234567']
        )
        self.assertEqual(self.config.get_service('output-test')['vpc_configuration']['public_ip'], 'DISABLED')

    def test_environment_simple_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['config'][0], 'FOOBAR=hi_mom')
        self.assertEqual(self.config.get_service('foobar-prod')['config'][2], 'FOO_BAR_PREFIX=oh_no/test')
        self.assertEqual(self.config.get_service('foobar-prod')['config'][3], 'FOO_BAR_SECRET=)(#jlk329!!3$3093%%.__)')


class TestContainerDefinition_load_yaml_no_interpolate(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        state_file = os.path.join(current_dir, 'terraform.tfstate')
        config_yml = os.path.join(current_dir, 'interpolate.yml')
        env_file = os.path.join(current_dir, 'env_file.env')
        with open(state_file) as f:
            tfstate = json.loads(f.read())
        with Replacer() as r:
            get_mock = r('deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3', Mock())
            get_mock.return_value = tfstate
            self.config = Config.new(filename=config_yml, env_file=env_file, interpolate=False)

    def test_simple_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['cluster'], '${terraform.cluster_name}')

    def test_nested_dict_interpolation(self):
        self.assertEqual(
            self.config.get_service('foobar-prod')['load_balancer']['load_balancer_name'],
            '${terraform.elb_id}'
        )

    def test_nested_list_interpolation(self):
        self.assertEqual(
            self.config.get_service('foobar-prod')['containers'][0]['environment'][2],
            'SECRETS_BUCKET_NAME=${terraform.secrets_bucket_name}'
        )

    def test_environment_simple_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['config'][0], 'FOOBAR=${env.FOOBAR_ENV}')
        self.assertEqual(
            self.config.get_service('foobar-prod')['config'][2],
            'FOO_BAR_PREFIX=${env.FOO_BAR_PREFIX_ENV}/test'
        )


class TestTunnelParameters_load_yaml(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_yml = os.path.join(current_dir, 'interpolate.yml')
        env_file = os.path.join(current_dir, 'env_file.env')
        self.config = Config.new(filename=config_yml, env_file=env_file, interpolate=False)

    def test_tunnel_find_instance(self):
        yml = self.config.get_section_item('tunnels', 'test')
        self.assertEqual(yml['service'], 'foobar-prod')
        self.assertEqual(yml['host'], 'config.DB_HOST')
        self.assertEqual(yml['port'], 3306)
        self.assertEqual(yml['local_port'], 8888)
