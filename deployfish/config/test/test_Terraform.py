import json
import os
import unittest
from mock import Mock
from testfixtures import compare, Replacer

from deployfish.config.processors.terraform import TerraformS3State


YAML = {
    'statefile': 's3://foobar/baz',
    'lookups': {
        'lookup1': '{environment}-cluster-name',
        'lookup2': '{environment}-elb-id',
        'lookup3': '{environment}-autoscalinggroup-name',
        'lookup4': 'security-group-list'
    }
}


class TestTerraform_load_yaml(unittest.TestCase):

    def setUp(self):
        self.terraform = TerraformS3State(YAML, {})

    def test_lookups(self):
        compare(self.terraform.terraform_config['lookups'], {
            'lookup1': '{environment}-cluster-name',
            'lookup2': '{environment}-elb-id',
            'lookup3': '{environment}-autoscalinggroup-name',
            'lookup4': 'security-group-list',
        })


class TestTerraform_get_terraform_state(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'terraform.tfstate')
        with open(filename) as f:
            self.tfstate = json.loads(f.read())
        self.terraform = TerraformS3State(YAML, {})

    def test_lookup(self):
        with Replacer() as r:
            get_mock = r('deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3', Mock())
            get_mock.return_value = self.tfstate
            self.terraform.load({'environment': 'qa'})
        self.assertTrue('qa-cluster-name' in self.terraform.terraform_lookups)


class TestTerraform_get_terraform_state_v12(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'terraform.tfstate.0.12')
        with open(filename) as f:
            self.tfstate = json.loads(f.read())
        self.terraform = TerraformS3State(YAML, {})

    def test_lookup(self):
        with Replacer() as r:
            get_mock = r('deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3', Mock())
            get_mock.return_value = self.tfstate
            self.terraform.load({'environment': 'qa'})
        self.assertTrue('prod-rds-address' in self.terraform.terraform_lookups)


class TestTerraform_lookup(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'terraform.tfstate')
        with open(filename) as f:
            self.tfstate = json.loads(f.read())
        self.terraform = TerraformS3State(YAML, {})

    def test_lookup(self):
        with Replacer() as r:
            get_mock = r('deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3', Mock())
            get_mock.return_value = self.tfstate
            self.terraform.load({'environment': 'qa'})
        self.assertEqual(self.terraform.lookup('lookup1', {'{environment}': 'qa'}), 'foobar-cluster-qa')
        self.assertEqual(self.terraform.lookup('lookup1', {'{environment}': 'prod'}), 'foobar-cluster-prod')
        self.assertListEqual(self.terraform.lookup('lookup4', {}), ['sg-1234567', 'sg-2345678', 'sg-3456789'])
