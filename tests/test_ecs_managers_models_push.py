"""Coverage for ECS managers and model methods with large statement gaps."""

from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.models.ecs import (
    Cluster,
    ContainerInstance,
    InvokedTask,
    Service,
    ServiceHelperTask,
    StandaloneTask,
    TaskDefinition,
)
from deployfish.core.models.events import EventScheduleRule

from tests.fixtures import (
    SERVICE_YML_WITH_HELPER_TASKS,
    STANDALONE_TASK_YML,
)

TASK_DEF_ARN = "arn:aws:ecs:us-west-2:123:task-definition/foobar-test-mytask:1"


def _task_definition_with_tags(tags: list[dict[str, str]]) -> TaskDefinition:
    return TaskDefinition(
        {
            "family": "foobar-test-mytask",
            "revision": 1,
            "taskDefinitionArn": TASK_DEF_ARN,
            "tags": tags,
        },
        containers=[],
    )


def _paginate(pages: list[dict]) -> MagicMock:
    paginator = MagicMock()
    paginator.paginate.return_value = pages
    return paginator


class TestTaskDefinitionManagerGaps:
    def test_get_raises_when_client_exception(self, _mock_boto3_session: MagicMock) -> None:
        exc = type("ClientException", (Exception,), {})
        _mock_boto3_session.exceptions.ClientException = exc
        _mock_boto3_session.describe_task_definition.side_effect = exc("missing")
        with pytest.raises(TaskDefinition.DoesNotExist):
            TaskDefinition.objects.get(TASK_DEF_ARN)

    def test_delete_raises_read_only(self) -> None:
        td = TaskDefinition({"family": "f", "revision": 1, "taskDefinitionArn": TASK_DEF_ARN})
        with pytest.raises(TaskDefinition.ReadOnly):
            TaskDefinition.objects.delete(td)


class TestAbstractTaskManagerGaps:
    def test_get_raises_when_task_definition_missing(self) -> None:
        with patch.object(TaskDefinition.objects, "exists", return_value=False):
            with pytest.raises(StandaloneTask.DoesNotExist):
                StandaloneTask.objects.get("missing-family")

    def test_get_many_returns_tasks(self) -> None:
        task = MagicMock(spec=StandaloneTask)
        with patch.object(StandaloneTask.objects, "get", return_value=task):
            results = StandaloneTask.objects.get_many(["a", "b"])
        assert len(results) == 2

    def test_run_returns_invoked_tasks(self, _mock_boto3_session: MagicMock) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        _mock_boto3_session.run_task.return_value = {
            "tasks": [
                {
                    "taskArn": "arn:aws:ecs:us-west-2:123:task/cluster/run-1",
                    "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
                    "lastStatus": "PENDING",
                }
            ],
        }
        invoked = task.run()
        assert len(invoked) == 1
        assert isinstance(invoked[0], InvokedTask)

    def test_run_raises_without_task_definition(self) -> None:
        task = StandaloneTask({"name": "x", "cluster": "c"}, task_definition=None)
        with pytest.raises(StandaloneTask.ImproperlyConfigured):
            StandaloneTask.objects.run(task)

    def test_save_with_schedule(self) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        schedule = MagicMock()
        schedule.set_task_definition_arn = MagicMock()
        task.schedule = schedule
        assert task.task_definition is not None
        with (
            patch.object(EventScheduleRule.objects, "get", side_effect=EventScheduleRule.DoesNotExist),
            patch.object(task.task_definition, "save", return_value=TASK_DEF_ARN),
            patch.object(schedule, "save"),
        ):
            arn = StandaloneTask.objects.save(task)
        assert arn == TASK_DEF_ARN
        schedule.set_task_definition_arn.assert_called_once_with(TASK_DEF_ARN)

    def test_save_deletes_existing_schedule(self) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        rule = MagicMock()
        with (
            patch.object(EventScheduleRule.objects, "get", return_value=rule),
            patch.object(task.task_definition, "save", return_value=TASK_DEF_ARN),
        ):
            StandaloneTask.objects.save(task)
        rule.delete.assert_called_once()

    def test_delete_removes_schedule_when_exists(self) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        with (
            patch.object(EventScheduleRule.objects, "exists", return_value=True),
            patch.object(EventScheduleRule.objects, "delete") as delete_mock,
        ):
            StandaloneTask.objects.delete(task)
        delete_mock.assert_called_once_with(task.pk)

    def test_enable_and_disable_schedule(self) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        schedule = MagicMock()
        task.schedule = schedule
        with patch.object(StandaloneTask.objects, "get", return_value=task):
            StandaloneTask.objects.enable_schedule(task.pk)
            StandaloneTask.objects.disable_schedule(task.pk)
        schedule.enable.assert_called_once()
        schedule.disable.assert_called_once()


class TestStandaloneTaskManagerListAll:
    def test_list_all_via_resource_groups_tagging(self) -> None:
        tagging_client = MagicMock()
        tagging_client.get_paginator.return_value = _paginate(
            [
                {
                    "ResourceTagMappingList": [
                        {"ResourceARN": TASK_DEF_ARN},
                    ]
                }
            ]
        )
        session = MagicMock()
        session.client.return_value = tagging_client
        td = _task_definition_with_tags(
            [
                {"key": "deployfish:type", "value": "standalone"},
                {"key": "deployfish:cluster", "value": "foobar-cluster"},
                {"key": "deployfish:task-name", "value": "foobar-test-mytask"},
            ]
        )
        standalone = StandaloneTask(
            {
                "name": "foobar-test-mytask",
                "cluster": "foobar-cluster",
                "task_type": "standalone",
            },
            task_definition=td,
        )
        with (
            patch("deployfish.core.models.ecs.get_boto3_session", return_value=session),
            patch.object(StandaloneTask.objects, "get", return_value=standalone),
        ):
            tasks = StandaloneTask.objects.list_all(task_type="standalone")
        assert len(tasks) == 1

    def test_filter_list_results_by_service_name(self) -> None:
        td = _task_definition_with_tags([])
        task = StandaloneTask(
            {"name": "t", "cluster": "c", "service": "foobar-cluster:foobar-test", "task_type": "standalone"},
            task_definition=td,
        )
        filtered = StandaloneTask.objects.filter_list_results([task], "foobar-*", None, None)
        assert filtered == [task]

    def test_list_scheduled_filters_by_cluster_glob(self) -> None:
        td = _task_definition_with_tags(
            [
                {"key": "deployfish:type", "value": "standalone"},
                {"key": "deployfish:cluster", "value": "foobar-cluster"},
            ]
        )
        standalone = StandaloneTask(
            {
                "name": "t",
                "cluster": "foobar-cluster",
                "task_type": "standalone",
                "service": "foobar-cluster:svc",
            },
            task_definition=td,
        )
        with patch.object(
            StandaloneTask.objects,
            "list_scheduled",
            return_value=[standalone],
        ) as list_mock:
            tasks = StandaloneTask.objects.list(
                scheduled_only=True,
                cluster_name="foobar-*",
                task_type="standalone",
            )
        list_mock.assert_called_once()
        assert tasks == [standalone]


class TestServiceHelperTaskManagerListAll:
    def test_list_all_collects_helper_tasks(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        helper_arn = "arn:aws:ecs:us-west-2:123:task-definition/helper-migrate:1"
        td = TaskDefinition(
            {"family": "helper", "revision": 1, "taskDefinitionArn": helper_arn, "tags": {}},
            containers=[],
        )
        td.tags["deployfish:command:migrate"] = helper_arn
        service.cache["task_definition"] = td
        helper = MagicMock(spec=ServiceHelperTask)
        with (
            patch.object(Service.objects, "list", return_value=[service]),
            patch.object(ServiceHelperTask.objects, "get", return_value=helper),
        ):
            tasks = ServiceHelperTask.objects.list_all()
        assert tasks == [helper]


class TestServiceManagerListValidation:
    def test_list_invalid_launch_type(self) -> None:
        with pytest.raises(Service.OperationFailed, match="launch_type"):
            Service.objects.list(launch_type="INVALID")

    def test_list_invalid_scheduling_strategy(self) -> None:
        with pytest.raises(Service.OperationFailed, match="INVALID"):
            Service.objects.list(scheduling_strategy="INVALID")


class TestClusterManagerGaps:
    def test_get_many_sorted(self, _mock_boto3_session: MagicMock) -> None:
        _mock_boto3_session.describe_clusters.return_value = {
            "clusters": [
                {"clusterName": "b-cluster", "clusterArn": "arn:1"},
                {"clusterName": "a-cluster", "clusterArn": "arn:2"},
            ],
        }
        clusters = Cluster.objects.get_many(["b-cluster", "a-cluster"])
        assert [c.name for c in clusters] == ["a-cluster", "b-cluster"]

    def test_delete_raises_read_only(self) -> None:
        cluster = Cluster({"clusterName": "c", "clusterArn": "arn:1"})
        with pytest.raises(Cluster.ReadOnly):
            Cluster.objects.delete(cluster)


class TestTaskModelProperties:
    def test_render_for_display_with_schedule(self) -> None:
        td = TaskDefinition(
            {"family": "f", "revision": 1, "taskDefinitionArn": TASK_DEF_ARN, "containerDefinitions": []},
            containers=[],
        )
        schedule = MagicMock()
        schedule.data = {"ScheduleExpression": "rate(5 minutes)"}
        schedule.enabled = True
        task = StandaloneTask(
            {"name": "t", "cluster": "c", "service": "c:svc"},
            task_definition=td,
            schedule=schedule,
        )
        with patch.object(td, "render_for_display", return_value={"family": "f"}):
            display = task.render_for_display()
        assert display["schedule_expression"] == "rate(5 minutes)"
        assert display["serviceName"] == "svc"

    def test_unschedule_deletes_schedule(self) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        schedule = MagicMock()
        task.schedule = schedule
        task.unschedule()
        schedule.delete.assert_called_once()

    def test_standalone_secrets_prefix_and_reload(self) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        assert task.secrets_prefix.endswith(".")
        task.cache["secrets"] = {"a": MagicMock()}
        with patch.object(task.task_definition, "reload_secrets") as reload_mock:
            task.reload_secrets()
        assert "secrets" not in task.cache
        reload_mock.assert_called_once()


class TestInvokedTaskModelGaps:
    TASK_DATA = {
        "taskArn": "arn:aws:ecs:us-west-2:123:task/cluster/abc",
        "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
        "taskDefinitionArn": TASK_DEF_ARN,
        "lastStatus": "RUNNING",
        "availabilityZone": "us-west-2a",
    }

    def test_container_instance_none_for_fargate(self) -> None:
        task = InvokedTask(self.TASK_DATA)  # type: ignore[abstract]
        with patch.object(task, "get_cached", side_effect=KeyError):
            assert task.container_instance is None


class TestContainerInstanceModel:
    def test_ssh_target_is_ec2_instance(self) -> None:
        ci = ContainerInstance(
            {
                "containerInstanceArn": "arn:aws:ecs:us-west-2:123:container-instance/abc",
                "ec2InstanceId": "i-abc123",
            },
            cluster="foobar-cluster",
        )
        instance = MagicMock()
        with patch.object(ci, "get_cached", return_value=instance):
            assert ci.ssh_target is instance
