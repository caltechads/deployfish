"""Focused unit tests for deployfish.core.models.ecs coverage gaps."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.models.ecs import (
    ContainerDefinition,
    ContainerInstance,
    InvokedTask,
    Service,
    ServiceHelperTask,
    TaskDefinition,
)

from tests.fixtures import SERVICE_YML, SERVICE_YML_WITH_HELPER_TASKS

TASK_DEF_ARN = "arn:aws:ecs:us-west-2:123:task-definition/foobar-test:1"
CHUNK_SIZE = 10
LARGE_SERVICE_COUNT = 15


def _cluster_paginator(clusters: list[str]) -> MagicMock:
    paginator = MagicMock()
    cluster_arns = [f"arn:aws:ecs:us-west-2:123:cluster/{name}" for name in clusters]
    paginator.paginate.return_value = [{"clusterArns": cluster_arns}]
    return paginator


def _service_paginator(services: list[str]) -> MagicMock:
    paginator = MagicMock()
    paginator.paginate.return_value = [{"serviceArns": services}]
    return paginator


def _service_data(
    name: str = "foobar-test",
    cluster: str = "foobar-cluster",
    *,
    status: str = "ACTIVE",
    deployments: list[dict[str, Any]] | None = None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "serviceName": name,
        "clusterArn": f"arn:aws:ecs:us-west-2:123:cluster/{cluster}",
        "status": status,
        "taskDefinition": TASK_DEF_ARN,
        "desiredCount": 1,
        "runningCount": 1,
        "deployments": deployments or [],
        "events": events or [],
    }


def _task_definition(version: str = "0.1.0") -> TaskDefinition:
    return TaskDefinition(
        {
            "family": "foobar-test",
            "revision": 1,
            "taskDefinitionArn": TASK_DEF_ARN,
            "containerDefinitions": [
                {
                    "name": "foobar",
                    "image": f"foobar/foobar:{version}",
                    "cpu": 512,
                    "memory": 512,
                }
            ],
        },
        containers=[
            ContainerDefinition(
                {
                    "name": "foobar",
                    "image": f"foobar/foobar:{version}",
                    "cpu": 512,
                    "memory": 512,
                }
            )
        ],
    )


def _describe_services_by_name(**kwargs: Any) -> dict[str, list[dict[str, Any]]]:
    names = cast("list[str]", kwargs["services"])
    return {"services": [_service_data(name=name.rsplit("/", 1)[-1]) for name in names]}


@pytest.fixture
def ecs_client(_mock_boto3_session: MagicMock) -> MagicMock:
    return _mock_boto3_session


class TestServiceManagerListFilters:
    def test_list_filters_by_service_name_glob(self, ecs_client: MagicMock) -> None:
        ecs_client.exceptions.ClusterNotFoundException = type(
            "ClusterNotFoundException",
            (Exception,),
            {},
        )
        ecs_client.get_paginator.side_effect = [
            _cluster_paginator(["foobar-cluster"]),
            _service_paginator(["prefix/foobar-test", "prefix/other-service"]),
        ]
        ecs_client.describe_services.side_effect = _describe_services_by_name
        services = Service.objects.list(service_name="foobar-*")
        assert len(services) == 1
        assert services[0].name == "foobar-test"

    def test_list_filters_by_updated_since(self, ecs_client: MagicMock) -> None:
        ecs_client.exceptions.ClusterNotFoundException = type(
            "ClusterNotFoundException",
            (Exception,),
            {},
        )
        ecs_client.get_paginator.side_effect = [
            _cluster_paginator(["foobar-cluster"]),
            _service_paginator(["old-service", "new-service"]),
        ]
        old_time = datetime(2020, 1, 1, tzinfo=UTC)
        new_time = datetime(2025, 6, 1, tzinfo=UTC)
        service_map = {
            "old-service": _service_data(
                name="old-service",
                deployments=[{"status": "PRIMARY", "createdAt": old_time}],
            ),
            "new-service": _service_data(
                name="new-service",
                deployments=[{"status": "PRIMARY", "createdAt": new_time}],
            ),
        }

        def describe_services(**kwargs: Any) -> dict[str, list[dict[str, Any]]]:
            names = cast("list[str]", kwargs["services"])
            return {"services": [service_map[name] for name in names]}

        ecs_client.describe_services.side_effect = describe_services
        cutoff = datetime(2024, 1, 1, tzinfo=UTC)
        services = Service.objects.list(updated_since=cutoff)
        assert len(services) == 1
        assert services[0].name == "new-service"


class TestServiceManagerUpdate:
    def test_update_raises_when_service_not_active(self, ecs_client: MagicMock) -> None:
        exc = type("ServiceNotActiveException", (Exception,), {})
        ecs_client.exceptions.ServiceNotActiveException = exc
        ecs_client.update_service.side_effect = exc("inactive")
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        update_payload = {"cluster": "foobar-cluster"}
        with (
            patch.object(Service.objects, "exists", return_value=True),
            patch.object(service, "render_for_update", return_value=update_payload),
            pytest.raises(Service.OperationFailed, match="cannot be updated"),
        ):
            Service.objects.update(service)


class TestServiceManagerGetManyExtended:
    def test_get_many_chunks_and_returns_all_active_services(
        self,
        ecs_client: MagicMock,
    ) -> None:
        def describe_services(**kwargs: Any) -> dict[str, list[dict[str, Any]]]:
            names = cast("list[str]", kwargs["services"])
            return {"services": [_service_data(name=name) for name in names]}

        ecs_client.describe_services.side_effect = describe_services
        pks = [f"foobar-cluster:svc-{index}" for index in range(LARGE_SERVICE_COUNT)]
        services = Service.objects.get_many(pks)
        expected_chunks = (LARGE_SERVICE_COUNT + CHUNK_SIZE - 1) // CHUNK_SIZE
        assert ecs_client.describe_services.call_count == expected_chunks
        assert len(services) == LARGE_SERVICE_COUNT
        expected_names = {f"svc-{index}" for index in range(LARGE_SERVICE_COUNT)}
        assert {service.name for service in services} == expected_names

    def test_get_many_skips_inactive_services(self, ecs_client: MagicMock) -> None:
        ecs_client.describe_services.return_value = {
            "services": [
                _service_data(name="active-one"),
                _service_data(name="inactive-one", status="INACTIVE"),
            ],
        }
        pks = ["foobar-cluster:active-one", "foobar-cluster:inactive-one"]
        services = Service.objects.get_many(pks)
        assert len(services) == 1
        assert services[0].name == "active-one"


class TestContainerInstanceManager:
    CONTAINER_INSTANCE_DATA = {
        "containerInstanceArn": "arn:aws:ecs:us-west-2:123:container-instance/abc",
        "ec2InstanceId": "i-1234567890abcdef0",
        "remainingResources": [
            {"name": "CPU", "type": "INTEGER", "integerValue": 1024},
        ],
    }

    def test_get_returns_container_instance(self, ecs_client: MagicMock) -> None:
        ecs_client.describe_container_instances.return_value = {
            "containerInstances": [self.CONTAINER_INSTANCE_DATA],
        }
        instance = ContainerInstance.objects.get("foobar-cluster:abc")
        assert instance.cluster == "foobar-cluster"
        assert instance.arn.endswith("abc")

    def test_get_raises_when_missing(self, ecs_client: MagicMock) -> None:
        client_exc = type("ClientException", (Exception,), {})
        ecs_client.exceptions.ClientException = client_exc
        ecs_client.describe_container_instances.side_effect = client_exc("missing")
        with pytest.raises(ContainerInstance.DoesNotExist):
            ContainerInstance.objects.get("foobar-cluster:missing")

    def test_get_raises_client_exception_as_does_not_exist(
        self,
        ecs_client: MagicMock,
    ) -> None:
        exc = type("ClientException", (Exception,), {})
        ecs_client.exceptions.ClientException = exc
        ecs_client.describe_container_instances.side_effect = exc("missing")
        with pytest.raises(ContainerInstance.DoesNotExist):
            ContainerInstance.objects.get("foobar-cluster:abc")

    def test_list_raises_when_cluster_missing(self, ecs_client: MagicMock) -> None:
        from deployfish.core.models.ecs import Cluster

        exc = type("ClusterNotFoundException", (Exception,), {})
        ecs_client.exceptions.ClusterNotFoundException = exc
        ecs_client.list_container_instances.side_effect = exc("missing cluster")
        with pytest.raises(Cluster.DoesNotExist):
            ContainerInstance.objects.list("missing-cluster")

    def test_exists_false_when_missing(self, ecs_client: MagicMock) -> None:
        client_exc = type("ClientException", (Exception,), {})
        ecs_client.exceptions.ClientException = client_exc
        ecs_client.describe_container_instances.side_effect = client_exc("missing")
        assert ContainerInstance.objects.exists("foobar-cluster:missing") is False

    def test_list_returns_container_instances(self, ecs_client: MagicMock) -> None:
        container_arn = self.CONTAINER_INSTANCE_DATA["containerInstanceArn"]
        ecs_client.list_container_instances.return_value = {
            "containerInstanceArns": [container_arn],
        }
        ecs_client.describe_container_instances.return_value = {
            "containerInstances": [self.CONTAINER_INSTANCE_DATA],
        }
        instances = ContainerInstance.objects.list("foobar-cluster")
        assert len(instances) == 1
        assert instances[0].cluster == "foobar-cluster"


class TestServiceHelperTaskManager:
    def test_list_all_collects_command_tags_from_services(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        helper_arn = "arn:aws:ecs:us-west-2:123:task-definition/helper-migrate:1"
        td = _task_definition()
        td.tags["deployfish:command:migrate"] = helper_arn
        service.cache["task_definition"] = td
        with (
            patch.object(Service.objects, "list", return_value=[service]),
            patch.object(ServiceHelperTask.objects, "get") as get_mock,
        ):
            helper_task = MagicMock(spec=ServiceHelperTask)
            get_mock.return_value = helper_task
            tasks = ServiceHelperTask.objects.list_all()
        get_mock.assert_called_once_with(helper_arn)
        assert tasks == [helper_task]


class TestServicePropertiesExtended:
    def test_version_delegates_to_task_definition(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        td = _task_definition("2.3.4")
        service.cache["task_definition"] = td
        assert service.version == "2.3.4"

    def test_last_updated_from_primary_deployment(self) -> None:
        created_at = datetime(2025, 5, 1, tzinfo=UTC)
        service = Service(
            _service_data(
                deployments=[
                    {"status": "PRIMARY", "createdAt": created_at},
                    {
                        "status": "ACTIVE",
                        "createdAt": datetime(2025, 4, 1, tzinfo=UTC),
                    },
                ]
            )
        )
        assert service.last_updated == created_at

    def test_last_updated_none_without_primary_deployment(self) -> None:
        active_created = datetime(2025, 5, 1, tzinfo=UTC)
        service = Service(
            _service_data(
                deployments=[{"status": "ACTIVE", "createdAt": active_created}]
            )
        )
        assert service.last_updated is None

    def test_deployments_and_events_return_service_data(self) -> None:
        deployments = [{"status": "PRIMARY", "id": "ecs-svc/1"}]
        events = [{"message": "service reached steady state"}]
        service = Service(_service_data(deployments=deployments, events=events))
        assert service.deployments == deployments
        assert service.events == events

    def test_cluster_uses_get_cached(self) -> None:
        service = Service(_service_data())
        service.data["cluster"] = "foobar-cluster"
        cluster = MagicMock()
        with patch.object(service, "get_cached", return_value=cluster) as cached:
            assert service.cluster is cluster
        cached.assert_called_once()


class TestInvokedTaskExtended:
    TASK_DATA = {
        "taskArn": "arn:aws:ecs:us-west-2:123:task/cluster/abc",
        "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
        "taskDefinitionArn": TASK_DEF_ARN,
        "lastStatus": "RUNNING",
    }

    def test_delete_stops_task(self, ecs_client: MagicMock) -> None:
        task = InvokedTask(self.TASK_DATA)  # type: ignore[abstract]
        cluster = MagicMock()
        cluster.name = "foobar-cluster"
        task.cache["cluster"] = cluster
        InvokedTask.objects.delete(task)
        ecs_client.stop_task.assert_called_once_with(
            cluster="foobar-cluster",
            task=task.arn,
        )

    def test_containers_delegates_to_task_definition(self) -> None:
        task = InvokedTask(self.TASK_DATA)  # type: ignore[abstract]
        td = _task_definition()
        with patch.object(TaskDefinition.objects, "get", return_value=td):
            assert task.containers == td.containers

    def test_cluster_uses_get_cached(self) -> None:
        task = InvokedTask(self.TASK_DATA)  # type: ignore[abstract]
        cluster = MagicMock()
        with patch.object(task, "get_cached", return_value=cluster) as cached:
            assert task.cluster is cluster
        cached.assert_called_once()


class TestTaskDefinitionManagerList:
    def test_list_uses_paginator_and_fetches_each_revision(
        self,
        ecs_client: MagicMock,
    ) -> None:
        paginator = MagicMock()
        ecs_client.get_paginator.return_value = paginator
        revision_one = f"{TASK_DEF_ARN.rsplit(':', 1)[0]}:1"
        revision_two = f"{TASK_DEF_ARN.rsplit(':', 1)[0]}:2"
        paginator.paginate.return_value = [
            {"taskDefinitionArns": [revision_one]},
            {"taskDefinitionArns": [revision_two]},
        ]
        td = _task_definition()
        with patch.object(TaskDefinition.objects, "get", return_value=td) as get_mock:
            results = TaskDefinition.objects.list("foobar-test")
        ecs_client.get_paginator.assert_called_once_with("list_task_definitions")
        paginator.paginate.assert_called_once_with(
            familyPrefix="foobar-test",
            sort="ASC",
        )
        revision_count = 2
        assert get_mock.call_count == revision_count
        assert len(results) == revision_count
