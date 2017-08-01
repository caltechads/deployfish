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
        with open(state_file) as f:
            tfstate = json.loads(f.read())
        os.environ['FOOBAR_ENV'] = "hi_mom"
        with Replacer() as r:
            get_mock = r('deployfish.terraform.Terraform._get_state_file_from_s3', Mock())
            get_mock.return_value = tfstate
            self.config = Config(filename=config_yml)

    def tearDown(self):
        del os.environ['FOOBAR_ENV']

    def test_terraform_simple_interpolation(self):
        self.assertEqual(self.config.get_service('cit-auth-prod')['cluster'], 'foobar-proxy-prod')

    def test_terraform_nested_dict_interpolation(self):
        self.assertEqual(self.config.get_service('cit-auth-prod')['load_balancer']['load_balancer_name'], 'foobar-proxy-prod')

    def test_terraform_nested_list_interpolation(self):
        self.assertEqual(self.config.get_service('cit-auth-prod')['containers'][0]['environment'][2], 'SECRETS_BUCKET_NAME=ac-config-store')

    def test_environment_simple_interpolation(self):
        self.assertEqual(self.config.get_service('cit-auth-prod')['config'][0], 'FOOBAR=hi_mom')


class TestContainerDefinition_load_yaml_no_interpolate(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        state_file = os.path.join(current_dir, 'terraform.tfstate')
        config_yml = os.path.join(current_dir, 'interpolate.yml')
        with open(state_file) as f:
            tfstate = json.loads(f.read())
        os.environ['FOOBAR_ENV'] = "hi_mom"
        with Replacer() as r:
            get_mock = r('deployfish.terraform.Terraform._get_state_file_from_s3', Mock())
            get_mock.return_value = tfstate
            self.config = Config(filename=config_yml, interpolate=False)

    def tearDown(self):
        del os.environ['FOOBAR_ENV']

    def test_simple_interpolation(self):
        self.assertEqual(self.config.get_service('cit-auth-prod')['cluster'], '${terraform.proxy_cluster_name}')

    def test_nested_dict_interpolation(self):
        self.assertEqual(self.config.get_service('cit-auth-prod')['load_balancer']['load_balancer_name'], '${terraform.proxy_elb_id}')

    def test_nested_list_interpolation(self):
        self.assertEqual(self.config.get_service('cit-auth-prod')['containers'][0]['environment'][2], 'SECRETS_BUCKET_NAME=${terraform.secrets_bucket_name}')

    def test_environment_simple_interpolation(self):
        self.assertEqual(self.config.get_service('cit-auth-prod')['config'][0], 'FOOBAR=${env.FOOBAR_ENV}')
