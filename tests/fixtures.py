"""Shared YAML dict fixtures for deployfish tests."""

from copy import deepcopy
from typing import Any

SERVICE_YML: dict[str, Any] = {
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
            "ports": ["443:8080", "8125:8125/udp", "8081"],
            "environment": ["AWS_DEFAULT_REGION=us-west-2"],
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

FARGATE_SERVICE_YML: dict[str, Any] = {
    **deepcopy(SERVICE_YML),
    "launch_type": "FARGATE",
    "network_mode": "awsvpc",
    "vpc_configuration": {
        "subnets": ["subnet-abc123"],
        "security_groups": ["sg-abc123"],
    },
}

APPLICATION_SCALING_YML: dict[str, Any] = {
    "min_capacity": 2,
    "max_capacity": 4,
    "role_arn": "arn:aws:iam::123445678901:role/ApplicationAutoscalingECSRole",
    "scale-up": {
        "cpu": ">=60",
        "check_every_seconds": 60,
        "periods": 5,
        "cooldown": 60,
        "scale_by": 1,
    },
    "scale-down": {
        "cpu": "<=30",
        "check_every_seconds": 60,
        "periods": 60,
        "cooldown": 60,
        "scale_by": -1,
    },
}

SERVICE_YML_WITH_SCALING: dict[str, Any] = {
    **deepcopy(SERVICE_YML),
    "application_scaling": deepcopy(APPLICATION_SCALING_YML),
}

HELPER_TASKS_YML: dict[str, Any] = {
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

SERVICE_YML_WITH_HELPER_TASKS: dict[str, Any] = {
    **deepcopy(SERVICE_YML),
    **deepcopy(HELPER_TASKS_YML),
}

CONFIG_SECRETS_YML: list[str] = [
    "DEBUG=False",
    "DB_HOST=my_rds_host",
    "DB_PASSWORD:secure=secret_value",
    "DB_PASSWORD:secure:arn:aws:kms:us-west-2:111122223333:key/abc=kms_secret",
    "/path/to/external:external",
]

STANDALONE_TASK_YML: dict[str, Any] = {
    "name": "foobar-test-mytask",
    "cluster": "foobar-cluster",
    "service": "foobar-cluster:foobar-test",
    "environment": "test",
    "count": 1,
    "family": "foobar-test-mytask",
    "network_mode": "bridge",
    "task_role_arn": "MY_TASK_ROLE_ARN",
    "execution_role": "MY_EXECUTION_ROLE_ARN",
    "containers": [
        {
            "name": "foobar",
            "image": "foobar/foobar:0.1.0",
            "cpu": 512,
            "memory": 512,
            "environment": ["AWS_DEFAULT_REGION=us-west-2"],
            "logging": {
                "driver": "awslogs",
                "options": {
                    "awslog-group": "my_log_group",
                    "awslog-stream": "my_log_stream",
                    "awslog-region": "us-west-2",
                },
            },
        }
    ],
    "config": ["DEBUG=False"],
}
