import os
import unittest
import yaml
from testfixtures import compare

from deployfish.aws.ecs import TaskDefinition


class TestTaskDefinition_load_yaml(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        with open(filename) as f:
            yml = yaml.load(f, Loader=yaml.FullLoader)
            # This should be the foobar-prod service
            self.td = TaskDefinition(yml=yml['services'][0])

    def test_family(self):
        self.assertEqual(self.td.family, 'foobar-prod')

    def test_taskRoleArn(self):
        self.assertEqual(self.td.taskRoleArn, 'a_task_role_arn')

    def test_networkMode(self):
        self.assertEqual(self.td.networkMode, 'host')

    def test_containers_were_loaded(self):
        self.assertEqual(len(self.td.containers), 1)


class TestTaskDefinition_load_yaml_ec2_execution_role(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        with open(filename) as f:
            yml = yaml.load(f, Loader=yaml.FullLoader)
            yml['services'][0]['execution_role'] = 'ecs_execution_role'
            # This should be the foobar-prod service
            self.td = TaskDefinition(yml=yml['services'][0])

    def test_executionRoleArn(self):
        self.assertEqual(self.td.executionRoleArn, 'ecs_execution_role')


class TestTaskDefinition_load_yaml_alternate(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        with open(filename) as f:
            yml = yaml.load(f, Loader=yaml.FullLoader)
            # This should be the foobar-prod2 service
            self.td = TaskDefinition(yml=yml['services'][1])

    def test_family(self):
        self.assertEqual(self.td.family, 'foobar-prod2')

    def test_taskRoleArn(self):
        self.assertEqual(self.td.taskRoleArn, None)

    def test_networkMode(self):
        self.assertEqual(self.td.networkMode, 'awsvpc')

    def test_executionRoleArn(self):
        self.assertEqual(self.td.executionRoleArn, 'ecs_execution_role')

    def test_cpu(self):
        self.assertEqual(self.td.cpu, 256)

    def test_memory(self):
        self.assertEqual(self.td.memory, 512)


class TestTaskDefinition_render(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        with open(filename) as f:
            self.yml = yaml.load(f, Loader=yaml.FullLoader)
            # This should be the foobar-prod service
            self.td = TaskDefinition(yml=self.yml['services'][0])

    def test_family(self):
        self.assertEqual(self.td.render()['family'], 'foobar-prod')

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
        compare(td.render()['volumes'], [{
            'name': '_host_path',
            'host': {'sourcePath': '/host/path'}
        }, {
            'name': '_host_path-ro',
            'host': {'sourcePath': '/host/path-ro'}
        }])


class TestTaskDefinition_render_alternate(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        with open(filename) as f:
            self.yml = yaml.load(f, Loader=yaml.FullLoader)
            # This should be the foobar-prod2 service
            self.td = TaskDefinition(yml=self.yml['services'][1])

    def test_family(self):
        self.assertEqual(self.td.render()['family'], 'foobar-prod2')

    def test_networkMode(self):
        self.assertEqual(self.td.render()['networkMode'], 'awsvpc')

    def test_executionRoleArn(self):
        self.assertEqual(self.td.render()['executionRoleArn'], 'ecs_execution_role')

    def test_cpu(self):
        self.assertEqual(self.td.render()['cpu'], '256')

    def test_memory(self):
        self.assertEqual(self.td.render()['memory'], '512')


class TestTaskDefinition_explicit_volumes(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        with open(filename) as f:
            yml = yaml.load(f, Loader=yaml.FullLoader)
            # This should be the explicit-volumes service
            self.td = TaskDefinition(yml=yml['services'][2])

    def test_task_defines_volumes(self):
        self.assertTrue('volumes' in self.td.render())
        self.assertEqual(len(self.td.render()['volumes']), 3)
        compare(self.td.render()['volumes'], [{
            'name': 'storage_local',
            'host': {'sourcePath': '/foo/bar'}
        }, {
            'name': 'storage_task',
            'dockerVolumeConfiguration': {
                'scope': 'task',
                'autoprovision': True,
                'driver': 'my_vol_driver:latest'
            }
        }, {
            'name': 'storage_shared',
            'dockerVolumeConfiguration': {
                'scope': 'shared',
                'driver': 'my_vol_driver:latest',
                'driverOpts': {
                    'opt1': 'value1',
                    'opt2': 'value2',
                },
                'labels': {
                    'key1': 'val1',
                    'key2': 'val2',
                }
            }
        },
        ])

    def test_container_mounts(self):
        r = self.td.render()
        self.assertTrue('mountPoints' in r['containerDefinitions'][0])
        mp = r['containerDefinitions'][0]['mountPoints']
        self.assertEqual(len(mp), 3)
        compare(mp, [
            {'sourceVolume': 'storage_local', 'containerPath': '/container/path', 'readOnly': False},
            {'sourceVolume': 'storage_task', 'containerPath': '/container/path2', 'readOnly': False},
            {'sourceVolume': 'storage_shared', 'containerPath': '/container/path3', 'readOnly': True}
        ])
