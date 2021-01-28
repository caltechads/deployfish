import json
import os
import unittest
from mock import Mock
from testfixtures import compare, Replacer

from deployfish.terraform import Terraform


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
        with Replacer() as r:
            r.replace('deployfish.terraform.Terraform.get_terraform_state', Mock())
            self.terraform = Terraform('my-statefile-name', yml=YAML)

    def test_lookups(self):
        compare(self.terraform.lookups, {
            'lookup1': '{environment}-cluster-name',
            'lookup2': '{environment}-elb-id',
            'lookup3': '{environment}-autoscalinggroup-name',
            'lookup4': 'security-group-list',
        })


class TestTerraform_get_terraform_state(unittest.TestCase):

    def setUp(self):
        with Replacer() as r:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            filename = os.path.join(current_dir, 'terraform.tfstate')
            with open(filename) as f:
                tfstate = json.loads(f.read())
            get_mock = r('deployfish.terraform.Terraform._get_state_file_from_s3', Mock())
            get_mock.return_value = tfstate
            self.terraform = Terraform('my-statefile-name', yml=YAML)

    def test_lookup(self):
        self.assertTrue('qa-cluster-name' in self.terraform)


class TestTerraform_get_terraform_state_v12(unittest.TestCase):

    def setUp(self):
        with Replacer() as r:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            filename = os.path.join(current_dir, 'terraform.tfstate.0.12')
            with open(filename) as f:
                tfstate = json.loads(f.read())
            get_mock = r('deployfish.terraform.Terraform._get_state_file_from_s3', Mock())
            get_mock.return_value = tfstate
            self.terraform = Terraform('my-statefile-name', yml=YAML)

    def test_lookup(self):
        self.assertTrue('prod-rds-address' in self.terraform)


class TestTerraform_lookup(unittest.TestCase):

    def setUp(self):
        with Replacer() as r:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            filename = os.path.join(current_dir, 'terraform.tfstate')
            with open(filename) as f:
                tfstate = json.loads(f.read())
            get_mock = r('deployfish.terraform.Terraform._get_state_file_from_s3', Mock())
            get_mock.return_value = tfstate
            self.terraform = Terraform('my-statefile-name', yml=YAML)

    def test_lookup(self):
        self.assertEqual(self.terraform.lookup('lookup1', {'environment': 'qa'}), 'foobar-cluster-qa')
        self.assertEqual(self.terraform.lookup('lookup1', {'environment': 'prod'}), 'foobar-cluster-prod')
        self.assertListEqual(self.terraform.lookup('lookup4', {}), ['sg-1234567', 'sg-2345678', 'sg-3456789'])
