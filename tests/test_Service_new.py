from copy import deepcopy

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.ecs import Service

SERVICE_YML = {
    "name": "foobar-test",
    "cluster": "foobar-cluster",
    "environment": "test",
    "count": 1,
    "load_balancer": {
        "target_groups": [
            {
                "target_group_arn": "MY_TARGET_GROUP_ARN",
                "container_name": "foobar",
                "container_port": 8080,
            }
        ]
    },
    "family": "foobar-test",
    "network_mode": "host",
    "task_role_arn": "MY_TASK_ROLE_ARN",
    "execution_role": "MY_EXECUTION_ROLE_ARN",
    "containers": [
        {
            "name": "foobar",
            "image": "foobar/foobar:0.1.0",
            "cpu": 512,
            "memory": 512,
            "ports": [
                "443:8080",
                "8125:8125/udp",
                "8081",
            ],
            "environment": [
                "AWS_DEFAULT_REGION=us-west-2",
            ],
            "logging": {
                "driver": "fluentd",
                "options": {
                    "fluentd-address": "127.0.0.1:24224",
                    "tag": "foobar",
                },
            },
        }
    ],
    "config": [
        "DEBUG=False",
        "DB_HOST=my_rds_host",
        "DB_NAME=foobar",
        "DB_USER=foobar_u",
        "DB_PASSWORD:secure:arn:my_key=the_db_password",
        "DJANGO_SECRET_KEY=the_secret_key",
        "XFF_TRUSTED_PROXY_DEPTH=4",
        "STATSD_HOST=statsd.example.com",
        "STATSD_PREFIX=foobar.test",
    ],
}


class TestService_new:
    def test_service_name_is_set_correctly(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.name == "foobar-test"

    def test_service_pk_is_set_correctly(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.pk == "foobar-cluster:foobar-test"

    def test_service_environment_is_set_correctly(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.deployfish_environment == "test"

    def test_service_desiredCount_is_set_correctly(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.data["desiredCount"] == 1

    def test_service_loadBalancers_are_set_correctly(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert "loadBalancers" in service.data
        assert len(service.data["loadBalancers"]) == 1
        assert service.data["loadBalancers"][0] == {
            "targetGroupArn": "MY_TARGET_GROUP_ARN",
            "containerName": "foobar",
            "containerPort": 8080,
        }

    def test_task_definition_family_is_set_correctly(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.task_definition.data["family"] == "foobar-test"

    def test_task_definition_networkMode_is_set_correctly(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.task_definition.data["networkMode"] == "host"

    def test_task_definition_taskRoleArn_is_set_correctly(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.task_definition.data["taskRoleArn"] == "MY_TASK_ROLE_ARN"

    def test_task_definition_executionRoleArn_is_set_correctly(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert (
            service.task_definition.data["executionRoleArn"] == "MY_EXECUTION_ROLE_ARN"
        )

    def test_task_definition_containers_number_is_correct(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert len(service.task_definition.containers) == 1

    def test_task_definition_container_name_is_correct(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.task_definition.containers[0].data["name"] == "foobar"

    def test_task_definition_container_image_is_correct(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert (
            service.task_definition.containers[0].data["image"] == "foobar/foobar:0.1.0"
        )

    def test_task_definition_container_cpu_is_correct(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.task_definition.containers[0].data["cpu"] == 512

    def test_task_definition_container_memory_is_correct(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.task_definition.containers[0].data["memory"] == 512

    def test_task_definition_container_portMappings_is_correct(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.task_definition.containers[0].data["portMappings"] == [
            {"containerPort": 8080, "hostPort": 443, "protocol": "tcp"},
            {"containerPort": 8125, "hostPort": 8125, "protocol": "udp"},
            {"containerPort": 8081, "protocol": "tcp"},
        ]

    def test_task_definition_container_environment_is_correct(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        environment = service.task_definition.containers[0].data["environment"]
        assert {"name": "AWS_DEFAULT_REGION", "value": "us-west-2"} in environment
        assert {
            "name": "DEPLOYFISH_SERVICE_NAME",
            "value": "foobar-test",
        } in environment
        assert {"name": "DEPLOYFISH_ENVIRONMENT", "value": "test"} in environment
        assert {
            "name": "DEPLOYFISH_CLUSTER_NAME",
            "value": "foobar-cluster",
        } in environment

    def test_task_definition_container_logConfiguration_is_correct(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        assert service.task_definition.containers[0].data["logConfiguration"] == {
            "logDriver": "fluentd",
            "options": {
                "fluentd-address": "127.0.0.1:24224",
                "tag": "foobar",
            },
        }

    def test_secrets_are_correct(self) -> None:
        data = deepcopy(SERVICE_YML)
        service = Service.new(data, "deployfish")
        secret_names = sorted(service.secrets.keys())
        assert secret_names == [
            "DB_HOST",
            "DB_NAME",
            "DB_PASSWORD",
            "DB_USER",
            "DEBUG",
            "DJANGO_SECRET_KEY",
            "STATSD_HOST",
            "STATSD_PREFIX",
            "XFF_TRUSTED_PROXY_DEPTH",
        ]
        assert service.secrets["DB_HOST"].value == "my_rds_host"
        assert service.secrets["DB_NAME"].value == "foobar"
        assert service.secrets["DB_USER"].value == "foobar_u"
        assert service.secrets["DB_PASSWORD"].value == "the_db_password"
        assert service.secrets["DB_PASSWORD"].kms_key_id == "arn:my_key"
        assert service.secrets["DB_PASSWORD"].is_secure is True
        assert service.secrets["DEBUG"].value == "False"
        assert service.secrets["DJANGO_SECRET_KEY"].value == "the_secret_key"
        assert service.secrets["STATSD_HOST"].value == "statsd.example.com"
        assert service.secrets["STATSD_PREFIX"].value == "foobar.test"
        assert service.secrets["XFF_TRUSTED_PROXY_DEPTH"].value == "4"


SERVICE_YML_WITH_HELPER_TASKS = {
    **SERVICE_YML,
    "tasks": [
        {
            "family": "foobar-tasks-test",
            "containers": [
                {
                    "name": "foobar",
                    "cpu": 1024,
                    "memory": 2048,
                },
            ],
            "commands": [
                {
                    "name": "migrate",
                    "containers": [
                        {
                            "name": "foobar",
                            "command": "manage.py migrate",
                        }
                    ],
                },
                {
                    "name": "update_index",
                    "containers": [
                        {
                            "name": "foobar",
                            "command": "manage.py update_index",
                        }
                    ],
                },
            ],
        }
    ],
}


class TestService_new_with_helper_tasks:
    def test_service_name_is_set_correctly(self) -> None:
        data = deepcopy(SERVICE_YML_WITH_HELPER_TASKS)
        service = Service.new(data, "deployfish")
        assert service.name == "foobar-test"
