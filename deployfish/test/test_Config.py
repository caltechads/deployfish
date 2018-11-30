import json
from mock import Mock
import os
from testfixtures import Replacer
import unittest

from deployfish.config import Config


class TestContainerDefinition_load_yaml(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        state_file = os.path.join(current_dir, 'terraform.tfstate')
        config_yml = os.path.join(current_dir, 'interpolate.yml')
        env_file = os.path.join(current_dir, 'env_file.env')
        with open(state_file) as f:
            tfstate = json.loads(f.read())
        with Replacer() as r:
            get_mock = r('deployfish.terraform.Terraform._get_state_file_from_s3', Mock())
            get_mock.return_value = tfstate
            self.config = Config(filename=config_yml, env_file=env_file)

    def tearDown(self):
        pass

    def test_terraform_simple_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['cluster'], 'foobar-proxy-prod')

    def test_terraform_nested_dict_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['load_balancer']['load_balancer_name'], 'foobar-proxy-prod')

    def test_terraform_nested_list_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['containers'][0]['environment'][2], 'SECRETS_BUCKET_NAME=ac-config-store')

    def test_terraform_list_output_interpolation(self):
        self.assertListEqual(self.config.get_service('foobar-prod')['vpc_configuration']['security_groups'], ['sg-1234567', 'sg-2345678', 'sg-3456789'])

    def test_terraform_map_output_interpolation(self):
        self.assertListEqual(self.config.get_service('cit-output-test')['vpc_configuration']['subnets'], ['subnet-1234567'])
        self.assertListEqual(self.config.get_service('cit-output-test')['vpc_configuration']['security_groups'], ['sg-1234567'])
        self.assertEqual(self.config.get_service('cit-output-test')['vpc_configuration']['public_ip'], 'DISABLED')

    def test_environment_simple_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['config'][0], 'FOOBAR=hi_mom')
        self.assertEqual(self.config.get_service('foobar-prod')['config'][2], 'FOO_BAR_PREFIX=oh_no/test')


class TestContainerDefinition_load_yaml_no_interpolate(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        state_file = os.path.join(current_dir, 'terraform.tfstate')
        config_yml = os.path.join(current_dir, 'interpolate.yml')
        env_file = os.path.join(current_dir, 'env_file.env')
        with open(state_file) as f:
            tfstate = json.loads(f.read())
        with Replacer() as r:
            get_mock = r('deployfish.terraform.Terraform._get_state_file_from_s3', Mock())
            get_mock.return_value = tfstate
            self.config = Config(filename=config_yml, env_file=env_file, interpolate=False)

    def test_simple_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['cluster'], '${terraform.proxy_cluster_name}')

    def test_nested_dict_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['load_balancer']['load_balancer_name'], '${terraform.proxy_elb_id}')

    def test_nested_list_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['containers'][0]['environment'][2], 'SECRETS_BUCKET_NAME=${terraform.secrets_bucket_name}')

    def test_environment_simple_interpolation(self):
        self.assertEqual(self.config.get_service('foobar-prod')['config'][0], 'FOOBAR=${env.FOOBAR_ENV}')
        self.assertEqual(self.config.get_service('foobar-prod')['config'][2], 'FOO_BAR_PREFIX=${env.FOO_BAR_PREFIX_ENV}/test')


class TestTunnelParameters_load_yqml(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_yml = os.path.join(current_dir, 'interpolate.yml')
        env_file = os.path.join(current_dir, 'env_file.env')
        self.config = Config(filename=config_yml, env_file=env_file, interpolate=False)

    def test_tunnel_find_instance(self):
        yml = self.config.get_section_item('tunnels', 'test')
        self.assertEqual(yml['service'], 'foobar-prod')
        self.assertEqual(yml['host'], 'config.DB_HOST')
        self.assertEqual(yml['port'], 3306)
        self.assertEqual(yml['local_port'], 8888)
