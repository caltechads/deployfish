import json
import os
import unittest
import yaml

from testfixtures import compare
from deployfish.aws.ecs import ContainerDefinition


class TestContainerDefinition_load_yaml(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        with open(filename) as f:
            yml = yaml.load(f, Loader=yaml.FullLoader)
        # This should be the container named "example" in the "foobar-prod" service
        self.cd = ContainerDefinition(yml=yml['services'][0]['containers'][0])

    def test_name(self):
        self.assertEqual(self.cd.name, 'example')

    def test_cpu(self):
        self.assertEqual(self.cd.cpu, 1024)

    def test_memory(self):
        self.assertEqual(self.cd.memory, 4000)

    def test_memoryReservation(self):
        self.assertEqual(self.cd.memoryReservation, 2000)

    def test_image(self):
        self.assertEqual(self.cd.image, 'example:1.2.3')

    def test_command(self):
        self.assertEqual(self.cd.command, '/usr/bin/supervisord')

    def test_entryPoint(self):
        self.assertEqual(self.cd.entryPoint, '/entrypoint.sh')

    def test_portMappings(self):
        self.assertTrue('22' in self.cd.portMappings)
        self.assertTrue('80:80' in self.cd.portMappings)
        self.assertTrue('443:443' in self.cd.portMappings)
        self.assertTrue('8021:8021/udp' in self.cd.portMappings)

    def test_ulimits(self):
        self.assertEqual(len(self.cd.ulimits), 2)
        self.assertTrue({'name': 'nproc', 'soft': 65535, 'hard': 65535} in self.cd.ulimits)
        self.assertTrue({'name': 'nofile', 'soft': 65535, 'hard': 65535} in self.cd.ulimits)

    def test_volumes(self):
        self.assertEqual(self.cd.volumes, [])

    def test_extraHosts(self):
        self.assertTrue('foobar:127.0.0.1' in self.cd.extraHosts)
        self.assertTrue('foobaz:127.0.0.2' in self.cd.extraHosts)

    def test_cap_add(self):
        self.assertEqual(self.cd.cap_add, ['SYS_ADMIN'])

    def test_cap_drop(self):
        self.assertEqual(self.cd.cap_drop, ['SYS_RAWIO'])

    def test_tmpfs(self):
        self.assertEqual(self.cd.tmpfs, [
            {'containerPath': '/tmpfs', 'size': 256, 'mountOptions': ['defaults', 'noatime']},
            {'containerPath': '/tmpfs_another', 'size': 128}
        ])


class TestContainerDefinition_render(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        with open(filename) as f:
            self.yml = yaml.load(f, Loader=yaml.FullLoader)
        self.cd = ContainerDefinition(yml=self.yml['services'][0]['containers'][0])

    def test_name(self):
        self.assertEqual(self.cd.render()['name'], 'example')

    def test_cpu(self):
        self.assertEqual(self.cd.render()['cpu'], 1024)

    def test_cap_add(self):
        compare(self.cd.render()['linuxParameters']['capabilities']['add'], ["SYS_ADMIN"])

    def test_cap_drop(self):
        compare(self.cd.render()['linuxParameters']['capabilities']['drop'], ["SYS_RAWIO"])

    def test_tmpfs(self):
        compare(self.cd.render()['linuxParameters']['tmpfs'], [
            {'containerPath': '/tmpfs', 'size': 256, 'mountOptions': ['defaults', 'noatime']},
            {'containerPath': '/tmpfs_another', 'size': 128}
        ])

    def test_memory(self):
        self.assertEqual(self.cd.render()['memory'], 4000)

    def test_memoryReservation(self):
        self.assertEqual(self.cd.render()['memoryReservation'], 2000)

    def test_image(self):
        self.assertEqual(self.cd.render()['image'], 'example:1.2.3')

    def test_command(self):
        self.assertEqual(self.cd.render()['command'], ['/usr/bin/supervisord'])

    def test_entryPoint(self):
        self.assertEqual(self.cd.render()['entryPoint'], ['/entrypoint.sh'])

    def test_portMappings(self):
        self.assertEqual(len(self.cd.render()['portMappings']), 4)
        compare(self.cd.render()['portMappings'], [
            {'containerPort': 22, 'protocol': 'tcp'},
            {'hostPort': 80, 'containerPort': 80, 'protocol': 'tcp'},
            {'hostPort': 443, 'containerPort': 443, 'protocol': 'tcp'},
            {'hostPort': 8021, 'containerPort': 8021, 'protocol': 'udp'},
        ]
        )

    def test_ulimits(self):
        self.assertEqual(len(self.cd.ulimits), 2)
        render = self.cd.render()['ulimits']
        self.assertTrue({'name': 'nproc', 'softLimit': 65535, 'hardLimit': 65535} in render)
        self.assertTrue({'name': 'nofile', 'softLimit': 65535, 'hardLimit': 65535} in render)

    def test_environment(self):
        render = self.cd.render()['environment']
        self.assertTrue({'name': 'LDAPTLS_REQCERT', 'value': 'never'} in render)
        self.assertTrue({'name': 'ENVIRONMENT', 'value': 'prod'} in render)
        self.assertTrue({'name': 'SECRETS_BUCKET_NAME', 'value': 'config-store'} in render)

    def test_dockerLabels(self):
        compare(self.cd.render()['dockerLabels'], {'edu.caltech.imss-ads': 'foobar'})

    def test_links(self):
        cd = ContainerDefinition(yml=self.yml['services'][1]['containers'][0])
        compare(cd.render()['links'], ['redis', 'db:database'])

    def test_mountPoints(self):
        cd = ContainerDefinition(yml=self.yml['services'][1]['containers'][0])
        self.assertEqual(len(cd.render()['mountPoints']), 2)
        compare(cd.render()['mountPoints'], [
            {'sourceVolume': '_host_path', 'containerPath': '/container/path', 'readOnly': False},
            {'sourceVolume': '_host_path-ro', 'containerPath': '/container/path-ro', 'readOnly': True},
        ])

    def test_extraHosts(self):
        self.assertEqual(len(self.cd.render()['extraHosts']), 2)
        compare(self.cd.render()['extraHosts'], [
            {'hostname': 'foobar', 'ipAddress': '127.0.0.1'},
            {'hostname': 'foobaz', 'ipAddress': '127.0.0.2'},
        ])

    def test_logging(self):
        render = self.cd.render()
        log_config = render['logConfiguration']
        self.assertIn('logDriver', log_config)
        self.assertEqual(log_config['logDriver'], 'fluentd')
        self.assertIn('options', log_config)
        options = log_config['options']
        self.assertIn('fluentd-address', options)
        self.assertIn('tag', options)
        self.assertEqual(options['fluentd-address'], '127.0.0.1:24224')
        self.assertEqual(options['tag'], 'foobar')


class TestContainerDefinition_load_yaml_alternates(unittest.TestCase):

    """
    This test loads the foobar-prod2 service from simple.yml.  The reason we have this test
    is to test different code paths than those executed loading the foobar-prod service.

    Specifically:

        * loading of an ALB
        * volumes
        * links
        * no extra_hosts
        * no ulimits
        * no entrypoint
        * no command
        * labels in a different format
    """

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'simple.yml')
        with open(filename) as f:
            yml = yaml.load(f, Loader=yaml.FullLoader)
        self.cd = ContainerDefinition(yml=yml['services'][1]['containers'][0])

    def test_cpu(self):
        self.assertEqual(self.cd.cpu, 256)

    def test_memory(self):
        self.assertEqual(self.cd.memory, 512)

    def test_name(self):
        self.assertEqual(self.cd.name, 'example')

    def test_image(self):
        self.assertEqual(self.cd.image, 'example:1.2.3')

    def test_command(self):
        self.assertEqual(self.cd.command, None)

    def test_entryPoint(self):
        self.assertEqual(self.cd.entryPoint, None)

    def test_ulimits(self):
        self.assertEqual(self.cd.ulimits, [])

    def test_environment(self):
        compare(self.cd.environment, {
            'LDAPTLS_REQCERT': 'never',
            'ENVIRONMENT': 'prod',
            'SECRETS_BUCKET_NAME': 'config-store'
        })

    def test_dockerLabels(self):
        compare(self.cd.dockerLabels, {'edu.caltech.imss-ads': 'foobar'})

    def test_links(self):
        compare(self.cd.links, ['redis', 'db:database'])

    def test_volumes(self):
        compare(self.cd.volumes, ['/host/path:/container/path', '/host/path-ro:/container/path-ro:ro'])

    def test_extraHosts(self):
        self.assertEqual(self.cd.extraHosts, [])


class TestContainerDefinition_load_aws(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'container_aws.json')
        with open(filename) as f:
            aws_container = json.loads(f.read())
        self.cd = ContainerDefinition(aws=aws_container)

    def test_cpu(self):
        self.assertEqual(self.cd.cpu, 256)

    def test_memory(self):
        self.assertEqual(self.cd.memory, 512)

    def test_name(self):
        self.assertEqual(self.cd.name, 'my-container')

    def test_image(self):
        self.assertEqual(self.cd.image, 'my-container:1.0.0')

    def test_command(self):
        self.assertEqual(self.cd.command, "/bin/bash command1 arg1")

    def test_entryPoint(self):
        self.assertEqual(self.cd.entryPoint, "/entrypoint.sh arg1")

    def test_ulimits(self):
        self.assertEqual(len(self.cd.ulimits), 1)
        compare(self.cd.ulimits, [{'name': 'nproc', 'soft': 65535, 'hard': 65535}])

    def test_environment(self):
        compare(self.cd.environment, {
            'AUTOPROXY_SERVER_NAME': 'test1.autoproxy-test.caltech.edu',
            'ENVIRONMENT': 'prod'
        })

    def test_dockerLabels(self):
        compare(self.cd.dockerLabels, {
            'edu.caltech.imss-ads': 'foobar',
            'edu.caltech.task.helper1.id': 'foobar-helper:1'
        })

    def test_links(self):
        compare(self.cd.links, ['db'])

    def test_volumes(self):
        compare(self.cd.volumes, [
            '/host/path:/container/path',
            '/host/path-ro:/container/path-ro:ro'
        ])

    def test_extraHosts(self):
        compare(self.cd.extraHosts, ['foobar:127.0.0.1', 'foobaa:127.0.0.2'])

    def test_logging(self):
        lc = self.cd.logConfiguration
        self.assertIsNotNone(lc)
        self.assertEqual(lc.driver, 'fluentd')
        self.assertEqual(lc.options['fluentd-address'], '127.0.0.1:24224')
        self.assertEqual(lc.options['tag'], 'my-container')


class TestContainerDefinition_tasks(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, 'container_aws.json')
        with open(filename) as f:
            aws_container = json.loads(f.read())
        self.cd = ContainerDefinition(aws_container)

    def test_get_helper_tasks(self):
        self.assertEqual(self.cd.get_helper_tasks(), {'foobar-helper': 'foobar-helper:1'})

    def test_update_task_labels(self):
        self.cd.update_task_labels(['foobar-helper:2'])
        self.assertEqual(self.cd.get_helper_tasks(), {'foobar-helper': 'foobar-helper:2'})
