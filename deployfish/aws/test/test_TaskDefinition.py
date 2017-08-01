import unittest
import os

from testfixtures import compare
import yaml

from deployfish.aws.ecs import TaskDefinition


class TestTaskDefinition_load_yaml(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fname = os.path.join(current_dir, 'simple.yml')
        with open(fname) as f:
            yml = yaml.load(f)
        self.td = TaskDefinition(yml=yml['services'][0])

    def test_family(self):
        self.assertEqual(self.td.family, 'cit-auth-prod')

    def test_taskRoleArn(self):
        self.assertEqual(self.td.taskRoleArn, 'a_task_role_arn')

    def test_networkMode(self):
        self.assertEqual(self.td.networkMode, 'host')

    def test_containers_were_loaded(self):
        self.assertEqual(len(self.td.containers), 1)


class TestTaskDefinition_load_yaml_alternate(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fname = os.path.join(current_dir, 'simple.yml')
        with open(fname) as f:
            yml = yaml.load(f)
        self.td = TaskDefinition(yml=yml['services'][1])

    def test_taskRoleArn(self):
        self.assertEqual(self.td.taskRoleArn, None)


class TestTaskDefinition_render(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fname = os.path.join(current_dir, 'simple.yml')
        with open(fname) as f:
            self.yml = yaml.load(f)
        self.td = TaskDefinition(yml=self.yml['services'][0])

    def test_family(self):
        self.assertEqual(self.td.render()['family'], 'cit-auth-prod')

    def test_taskRoleArn(self):
        self.assertEqual(self.td.render()['taskRoleArn'], 'a_task_role_arn')

    def test_no_taskRoleArn(self):
        td = TaskDefinition(yml=self.yml['services'][1])
        self.assertTrue('taskRoleArn' not in td.render())

    def test_networkMode(self):
        self.assertEqual(self.td.render()['networkMode'], 'host')

    def test_containerDefinitions(self):
        self.assertTrue('containerDefinitions' in self.td.render())
        self.assertEqual(len(self.td.render()['containerDefinitions']), 1)

    def test_no_volumes(self):
        self.assertTrue('volumes' not in self.td.render())

    def test_has_volume_definitions(self):
        td = TaskDefinition(yml=self.yml['services'][1])
        self.assertTrue('volumes' in td.render())
        self.assertEqual(len(td.render()['volumes']), 2)
        compare(td.render()['volumes'], [{'name': '_host_path', 'host': {'sourcePath': '/host/path'}}, {'name': '_host_path-ro', 'host': {'sourcePath': '/host/path-ro'}}])


class TestTaskDefinition_volumes(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fname = os.path.join(current_dir, 'simple.yml')
        with open(fname) as f:
            yml = yaml.load(f)
        self.td = TaskDefinition(yml=yml['services'][1])
