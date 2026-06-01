from copy import deepcopy

import pytest

from deployfish.core.models.mixins import TaskDefinitionFARGATEMixin
from deployfish.exceptions import SchemaException

TASK_DATA_EC2 = {
    "family": "foobar-test",
    "taskRoleArn": "MY_TASK_ROLE_ARN",
    "executionRoleArn": "MY_EXECUTION_ROLE_ARN",
    "networkMode": "bridge",
}

CONTAINER_DATA = [
    {
        "name": "foobar",
        "image": "foobar/foobar:0.1.0",
        "cpu": 512,
        "memory": 512,
        "essential": True,
        "portMappings": [
            {
                "containerPort": 8080,
                "hostPort": 8080,
                "protocol": "tcp",
            }
        ],
        "environment": [
            {
                "name": "AWS_DEFAULT_REGION",
                "value": "us-west-2",
            }
        ],
        "secrets": [
            {
                "name": "DEBUG",
                "valueFrom": "foobar-cluster.foobar.DEBUG",
            },
            {
                "name": "DB_HOST",
                "valueFrom": "foobar-cluster.foobar.DB_HOST",
            },
            {
                "name": "DB_USER",
                "valueFrom": "foobar-cluster.foobar.DB_USER",
            },
            {
                "name": "DB_PASSWORD",
                "valueFrom": "foobar-cluster.foobar.DB_PASSWORD",
            },
        ],
        "logConfiguration": {
            "logDriver": "fluentd",
            "options": {
                "fluentd-address": "127.0.0.1:24224",
                "tag": "foobar",
            },
        },
    }
]


class TestTaskDefinitionFARGATEMixin_EC2:
    def test_cpu_does_not_get_set(self) -> None:
        data = deepcopy(TASK_DATA_EC2)
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        mixin.set_task_cpu(data, container_data)
        assert "cpu" not in data

    def test_can_set_task_cpu(self) -> None:
        data = deepcopy(TASK_DATA_EC2)
        data["cpu"] = 1024
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        mixin.set_task_cpu(data, container_data)
        assert data["cpu"] == "1024"

    def test_cpu_too_small_raises_SchemaException(self) -> None:
        data = deepcopy(TASK_DATA_EC2)
        data["cpu"] = 1
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        with pytest.raises(SchemaException, match="Task cpu must be greater than"):
            mixin.set_task_cpu(data, container_data)

    def test_memory_does_not_get_set(self) -> None:
        data = deepcopy(TASK_DATA_EC2)
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        mixin.set_task_memory(data, container_data)
        assert "memory" not in data

    def test_can_set_task_memory(self) -> None:
        data = deepcopy(TASK_DATA_EC2)
        data["memory"] = "512"
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        mixin.set_task_memory(data, container_data)
        assert data["memory"] == "512"

    def test_memory_too_small_for_container_memory_raises_SchemaException(self) -> None:
        data = deepcopy(TASK_DATA_EC2)
        data["memory"] = 1
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        with pytest.raises(SchemaException, match="Task memory must be greater than"):
            mixin.set_task_memory(data, container_data)

    def test_memory_too_small_for_container_memoryReservation_raises_SchemaException(self) -> None:
        data = deepcopy(TASK_DATA_EC2)
        container_data = deepcopy(CONTAINER_DATA)
        del container_data[0]["memory"]
        container_data[0]["memoryReservation"] = 512
        data["memory"] = 1
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        with pytest.raises(SchemaException, match="Task memory must be greater than"):
            mixin.set_task_memory(data, container_data)


TASK_DATA_FARGATE = {
    **TASK_DATA_EC2,
    "requiresCompatibilities": ["FARGATE"],
}


class TestTaskDefinitionFARGATEMixin_FARGATE:
    def test_cpu_is_set_if_not_provided(self) -> None:
        data = deepcopy(TASK_DATA_FARGATE)
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        mixin.set_task_cpu(data, container_data)
        assert data["cpu"] == "512"

    def test_can_set_task_cpu(self) -> None:
        data = deepcopy(TASK_DATA_FARGATE)
        data["cpu"] = 1024
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        mixin.set_task_cpu(data, container_data)
        assert data["cpu"] == "1024"

    def test_invalid_cpu_raises_SchemaException(self) -> None:
        data = deepcopy(TASK_DATA_FARGATE)
        data["cpu"] = 1
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        with pytest.raises(SchemaException, match="is not valid for FARGATE"):
            mixin.set_task_cpu(data, container_data)

    def test_cpu_too_small_raises_SchemaException(self) -> None:
        data = deepcopy(TASK_DATA_FARGATE)
        data["cpu"] = 256
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        with pytest.raises(SchemaException, match="Task cpu must be greater than"):
            mixin.set_task_cpu(data, container_data)

    def test_memory_is_set_based_on_container_memory_if_not_provided(self) -> None:
        data = deepcopy(TASK_DATA_FARGATE)
        data["cpu"] = 512
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        mixin.set_task_memory(data, container_data)
        assert data["memory"] == "1024"

    def test_memory_is_set_based_on_container_memoryReservation_if_not_provided(self) -> None:
        data = deepcopy(TASK_DATA_FARGATE)
        container_data = deepcopy(CONTAINER_DATA)
        del container_data[0]["memory"]
        container_data[0]["memoryReservation"] = 512
        data["cpu"] = 512
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        mixin.set_task_memory(data, container_data)
        assert data["memory"] == "1024"

    def test_can_set_memory(self) -> None:
        data = deepcopy(TASK_DATA_FARGATE)
        data["cpu"] = 512
        data["memory"] = 1024
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        mixin.set_task_memory(data, container_data)
        assert data["memory"] == "1024"

    def test_invalid_memory_for_cpu_raises_SchemaException(self) -> None:
        data = deepcopy(TASK_DATA_FARGATE)
        data["cpu"] = 512
        data["memory"] = 512
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        container_data = deepcopy(CONTAINER_DATA)
        with pytest.raises(SchemaException, match="512MB is not valid"):
            mixin.set_task_memory(data, container_data)

    def test_memory_too_small_for_container_memory_raises_SchemaException(self) -> None:
        data = deepcopy(TASK_DATA_FARGATE)
        container_data = deepcopy(CONTAINER_DATA)
        container_data[0]["memory"] = 1025
        data["cpu"] = 512
        data["memory"] = 1024
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        with pytest.raises(SchemaException, match="Task memory must be greater than"):
            mixin.set_task_memory(data, container_data)

    def test_memory_too_small_for_container_memoryReservation_raises_SchemaException(self) -> None:
        data = deepcopy(TASK_DATA_FARGATE)
        container_data = deepcopy(CONTAINER_DATA)
        del container_data[0]["memory"]
        container_data[0]["memoryReservation"] = 1025
        data["cpu"] = 512
        data["memory"] = 1024
        mixin = TaskDefinitionFARGATEMixin()
        mixin.data = data
        with pytest.raises(SchemaException, match="Task memory must be greater than"):
            mixin.set_task_memory(data, container_data)
