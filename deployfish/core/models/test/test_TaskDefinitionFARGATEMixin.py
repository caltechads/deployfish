from copy import deepcopy
import logging
import unittest

from deployfish.exceptions import SchemaException  # noqa:F401
from deployfish.core.models.mixins import TaskDefinitionFARGATEMixin

logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)


class TestTaskDefinitionFARGATEMixin_EC2(unittest.TestCase):

    TASK_DATA = {
        'family': 'foobar-test',
        'taskRoleArn': 'MY_TASK_ROLE_ARN',
        'executionRoleArn': 'MY_EXECUTION_ROLE_ARN',
        'networkMode': 'bridge',
    }

    CONTAINER_DATA = [
        {
            'name': 'foobar',
            'image': 'foobar/foobar:0.1.0',
            'cpu': 512,
            'memory': 512,
            'essential': True,
            'portMappings': [
                {
                    'containerPort': 8080,
                    'hostPort': 8080,
                    'protocol': 'tcp'
                }
            ],
            'environment': [
                {
                    'name': 'AWS_DEFAULT_REGION',
                    'value': 'us-west-2'
                }
            ],
            'secrets': [
                {
                    'name': 'DEBUG',
                    'valueFrom': 'foobar-cluster.foobar.DEBUG'
                },
                {
                    'name': 'DB_HOST',
                    'valueFrom': 'foobar-cluster.foobar.DB_HOST'
                },
                {
                    'name': 'DB_USER',
                    'valueFrom': 'foobar-cluster.foobar.DB_USER'
                },
                {
                    'name': 'DB_PASSWORD',
                    'valueFrom': 'foobar-cluster.foobar.DB_PASSWORD'
                },
            ],
            'logConfiguration': {
                'logDriver': 'fluentd',
                'options': {
                    'fluentd-address': '127.0.0.1:24224',
                    'tag': 'foobar'
                }
            }
        }
    ]

    def test_cpu_does_not_get_set(self):
        data = deepcopy(self.TASK_DATA)
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        mixin.set_task_cpu(data, container_data)
        self.assertTrue('cpu' not in data)

    def test_can_set_task_cpu(self):
        data = deepcopy(self.TASK_DATA)
        data['cpu'] = 1024
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        mixin.set_task_cpu(data, container_data)
        self.assertEqual(data['cpu'], 1024)

    def test_cpu_too_small_raises_SchemaException(self):
        data = deepcopy(self.TASK_DATA)
        data['cpu'] = 1
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        with self.assertRaises(SchemaException) as cm:
            mixin.set_task_cpu(data, container_data)
        self.assertTrue('Task cpu must be greater than' in str(cm.exception))

    def test_memory_does_not_get_set(self):
        data = deepcopy(self.TASK_DATA)
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        mixin.set_task_memory(data, container_data)
        self.assertTrue('memory' not in data)

    def test_can_set_task_memory(self):
        data = deepcopy(self.TASK_DATA)
        data['memory'] = 512
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        mixin.set_task_memory(data, container_data)
        self.assertEqual(data['memory'], 512)

    def test_memory_too_small_for_container_memory_raises_SchemaException(self):
        data = deepcopy(self.TASK_DATA)
        data['memory'] = 1
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        with self.assertRaises(SchemaException) as cm:
            mixin.set_task_memory(data, container_data)
        self.assertTrue('Task memory must be greater than' in str(cm.exception))

    def test_memory_too_small_for_container_memoryReservation_raises_SchemaException(self):
        data = deepcopy(self.TASK_DATA)
        container_data = deepcopy(self.CONTAINER_DATA)
        del container_data[0]['memory']
        container_data[0]['memoryReservation'] = 512
        data['memory'] = 1
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        with self.assertRaises(SchemaException) as cm:
            mixin.set_task_memory(data, container_data)
        self.assertTrue('Task memory must be greater than' in str(cm.exception))


class TestTaskDefinitionFARGATEMixin_FARGATE(unittest.TestCase):

    TASK_DATA = {
        'family': 'foobar-test',
        'taskRoleArn': 'MY_TASK_ROLE_ARN',
        'executionRoleArn': 'MY_EXECUTION_ROLE_ARN',
        'networkMode': 'bridge',
        'requiresCompatibilities': ['FARGATE']
    }

    CONTAINER_DATA = [
        {
            'name': 'foobar',
            'image': 'foobar/foobar:0.1.0',
            'cpu': 512,
            'memory': 512,
            'essential': True,
            'portMappings': [
                {
                    'containerPort': 8080,
                    'hostPort': 8080,
                    'protocol': 'tcp'
                }
            ],
            'environment': [
                {
                    'name': 'AWS_DEFAULT_REGION',
                    'value': 'us-west-2'
                }
            ],
            'secrets': [
                {
                    'name': 'DEBUG',
                    'valueFrom': 'foobar-cluster.foobar.DEBUG'
                },
                {
                    'name': 'DB_HOST',
                    'valueFrom': 'foobar-cluster.foobar.DB_HOST'
                },
                {
                    'name': 'DB_USER',
                    'valueFrom': 'foobar-cluster.foobar.DB_USER'
                },
                {
                    'name': 'DB_PASSWORD',
                    'valueFrom': 'foobar-cluster.foobar.DB_PASSWORD'
                },
            ],
            'logConfiguration': {
                'logDriver': 'fluentd',
                'options': {
                    'fluentd-address': '127.0.0.1:24224',
                    'tag': 'foobar'
                }
            }
        }
    ]

    def test_cpu_is_set_if_not_provided(self):
        data = deepcopy(self.TASK_DATA)
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        mixin.set_task_cpu(data, container_data)
        self.assertEqual(data['cpu'], 512)

    def test_can_set_task_cpu(self):
        data = deepcopy(self.TASK_DATA)
        data['cpu'] = 1024
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        mixin.set_task_cpu(data, container_data)
        self.assertEqual(data['cpu'], 1024)

    def test_invalid_cpu_raises_SchemaException(self):
        data = deepcopy(self.TASK_DATA)
        data['cpu'] = 1
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        with self.assertRaises(SchemaException) as cm:
            mixin.set_task_cpu(data, container_data)
        self.assertTrue('is not valid for FARGATE' in str(cm.exception))

    def test_cpu_too_small_raises_SchemaException(self):
        data = deepcopy(self.TASK_DATA)
        data['cpu'] = 256
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        with self.assertRaises(SchemaException) as cm:
            mixin.set_task_cpu(data, container_data)
        self.assertTrue('Task cpu must be greater than' in str(cm.exception))

    def test_memory_is_set_based_on_container_memory_if_not_provided(self):
        data = deepcopy(self.TASK_DATA)
        # cpu must be set in order to set fargate task memory
        data['cpu'] = 512
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        mixin.set_task_memory(data, container_data)
        self.assertEqual(data['memory'], 1024)

    def test_memory_is_set_based_on_container_memoryReservation_if_not_provided(self):
        data = deepcopy(self.TASK_DATA)
        container_data = deepcopy(self.CONTAINER_DATA)
        del container_data[0]['memory']
        container_data[0]['memoryReservation'] = 512
        # cpu must be set in order to set fargate task memory
        data['cpu'] = 512
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        mixin.set_task_memory(data, container_data)
        self.assertEqual(data['memory'], 1024)

    def test_can_set_memory(self):
        data = deepcopy(self.TASK_DATA)
        # cpu must be set in order to set fargate task memory
        data['cpu'] = 512
        data['memory'] = 1024
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        mixin.set_task_memory(data, container_data)
        self.assertEqual(data['memory'], 1024)

    def test_invalid_memory_for_cpu_raises_SchemaException(self):
        data = deepcopy(self.TASK_DATA)
        data['cpu'] = 512
        data['memory'] = 512
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(self.CONTAINER_DATA)
        with self.assertRaises(SchemaException) as cm:
            mixin.set_task_memory(data, container_data)
        self.assertTrue('512MB is not valid' in str(cm.exception))

    def test_memory_too_small_for_container_memory_raises_SchemaException(self):
        data = deepcopy(self.TASK_DATA)
        container_data = deepcopy(self.CONTAINER_DATA)
        container_data[0]['memory'] = 1025
        data['cpu'] = 512
        data['memory'] = 1024
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        with self.assertRaises(SchemaException) as cm:
            mixin.set_task_memory(data, container_data)
        self.assertTrue('Task memory must be greater than' in str(cm.exception))

    def test_memory_too_small_for_container_memoryReservation_raises_SchemaException(self):
        data = deepcopy(self.TASK_DATA)
        container_data = deepcopy(self.CONTAINER_DATA)
        del container_data[0]['memory']
        container_data[0]['memoryReservation'] = 1025
        data['cpu'] = 512
        data['memory'] = 1024
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        with self.assertRaises(SchemaException) as cm:
            mixin.set_task_memory(data, container_data)
        self.assertTrue('Task memory must be greater than' in str(cm.exception))
