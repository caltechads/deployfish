"""Coverage tests for network, commands, and logs controller gaps."""

from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.controllers.commands import ECSServiceCommandLogs, ECSServiceCommands
from deployfish.controllers.logs import LogsCloudWatchLogGroup, LogsCloudWatchLogStream
from deployfish.controllers.network import ObjectDockerExecController
from deployfish.controllers.service import ECSServiceSSH
from deployfish.core.models.cloudwatchlogs import (
    CloudWatchLogGroup,
    CloudWatchLogStream,
)
from deployfish.core.models.ec2 import Instance
from deployfish.core.models.ecs import Service

from tests.controller_helpers import bind_controller, bind_service_loader
from tests.fixtures import SERVICE_YML_WITH_HELPER_TASKS


def _ssh_target(name: str = "worker") -> Instance:
    return Instance(
        {
            "InstanceId": "i-1",
            "PrivateIpAddress": "10.0.0.1",
            "PublicDnsName": "",
            "PrivateDnsName": "a.internal",
            "Tags": [{"Key": "Name", "Value": name}],
        }
    )


class TestObjectSSHControllerRun:
    def test_run_prints_output_for_single_target(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceSSH(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.command = ["echo", "hello"]
        cement_app.pargs.verbose = False
        cement_app.pargs.choose = False
        cement_app.pargs.all = False
        target = _ssh_target()
        service = MagicMock()
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            with patch(
                "deployfish.controllers.network.get_ssh_target",
                return_value=target,
            ):
                with patch.object(
                    target, "ssh_noninteractive", return_value=(True, "hello\nworld")
                ):
                    with patch(
                        "deployfish.controllers.network.click.style",
                        side_effect=lambda v, **_: v,
                    ):
                        controller.run()
        assert cement_app.print.call_count == 2

    def test_run_on_all_targets(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceSSH(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.command = ["uptime"]
        cement_app.pargs.verbose = False
        cement_app.pargs.choose = False
        cement_app.pargs.all = True
        targets = [_ssh_target("a"), _ssh_target("b")]
        service = MagicMock()
        service.ssh_targets = targets
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            with patch.object(
                targets[0],
                "ssh_noninteractive",
                return_value=(True, "ok"),
            ):
                with patch.object(
                    targets[1],
                    "ssh_noninteractive",
                    return_value=(False, "failed"),
                ):
                    with patch(
                        "deployfish.controllers.network.click.style",
                        side_effect=lambda v, **_: v,
                    ):
                        controller.run()
        assert cement_app.print.call_count == 2

    def test_run_prints_error_lines_in_red(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceSSH(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.command = ["false"]
        cement_app.pargs.verbose = True
        cement_app.pargs.choose = False
        cement_app.pargs.all = False
        target = _ssh_target()
        service = MagicMock()
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            with patch(
                "deployfish.controllers.network.get_ssh_target",
                return_value=target,
            ):
                with patch.object(
                    target, "ssh_noninteractive", return_value=(False, "boom")
                ):
                    with patch(
                        "deployfish.controllers.network.click.style",
                        side_effect=lambda v, **_: v,
                    ):
                        controller.run()
        printed = " ".join(
            str(call.args[0]) for call in cement_app.print.call_args_list
        )
        assert "ERROR:" in printed


class TestGetEcsExecTarget:
    def test_get_ecs_exec_target_returns_none_when_not_choosing(self) -> None:
        controller = ObjectDockerExecController()
        obj = MagicMock()
        task_arn, container_name = controller.get_ecs_exec_target(obj, choose=False)
        assert task_arn is None
        assert container_name is None

    def test_get_ecs_exec_target_prompts_when_choosing(self) -> None:
        controller = ObjectDockerExecController()
        controller.app = MagicMock()
        container = MagicMock()
        container.name = "app"
        container.version = "1"
        task = MagicMock()
        task.name = "task-a"
        task.pk = "arn:aws:ecs:us-west-2:123:task/cluster/abc123"
        task.arn = "arn:aws:ecs:us-west-2:123:task/cluster/abc123"
        task.availability_zone = "us-west-2a"
        task.containers = [container]
        obj = MagicMock()
        obj.running_tasks = [task]
        prompt = MagicMock()
        prompt.prompt.return_value = "1"
        with patch("deployfish.controllers.network.shell.Prompt", return_value=prompt):
            with patch("deployfish.controllers.network.tabulate"):
                with patch("deployfish.controllers.network.click.secho"):
                    task_arn, chosen = controller.get_ecs_exec_target(obj, choose=True)
        assert task_arn == task.arn
        assert chosen == "app"


class TestECSServiceCommandsGaps:
    def test_info_renders_helper_task(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceCommands(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.command = "migrate"
        cement_app.pargs.includes = None
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            controller.info()
        cement_app.render.assert_called_once()

    def test_update_saves_all_helper_tasks(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceCommands(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_deployfish", return_value=service):
            with patch.object(
                service.helper_tasks[0],
                "save",
                return_value="arn:aws:ecs:us-west-2:123:task-definition/family:1",
            ):
                with patch.object(
                    service.helper_tasks[1],
                    "save",
                    return_value="arn:aws:ecs:us-west-2:123:task-definition/family:2",
                ):
                    with patch("deployfish.controllers.commands.click.secho"):
                        with patch(
                            "deployfish.controllers.commands.click.style",
                            side_effect=lambda v, **_: v,
                        ):
                            controller.update()
        assert cement_app.print.call_count >= 3

    def test_enable_raises_when_no_schedule(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceCommands(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.command = "migrate"
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        command = type("Command", (), {"name": "migrate", "schedule": None})()
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            with patch(
                "deployfish.controllers.commands.get_task", return_value=command
            ):
                with patch(
                    "deployfish.controllers.commands.click.style",
                    side_effect=lambda v, **_: v,
                ):
                    controller.enable()
        printed = str(cement_app.print.call_args[0][0])
        assert "no schedule" in printed

    def test_enable_reports_enabled_schedule(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceCommands(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.command = "migrate"
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        command = MagicMock()
        command.name = "migrate"
        command.schedule = MagicMock()
        command.schedule.enabled = True
        command.schedule_expression = "rate(1 day)"
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            with patch(
                "deployfish.controllers.commands.get_task", return_value=command
            ):
                with patch(
                    "deployfish.controllers.commands.click.style",
                    side_effect=lambda v, **_: v,
                ):
                    controller.enable()
        command.enable_schedule.assert_called_once()
        assert cement_app.print.call_count == 2

    def test_disable_reports_disabled_schedule(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceCommands(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.command = "migrate"
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        command = MagicMock()
        command.name = "migrate"
        command.schedule = MagicMock()
        command.schedule.enabled = False
        command.schedule_expression = "rate(1 day)"
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            with patch(
                "deployfish.controllers.commands.get_task", return_value=command
            ):
                with patch(
                    "deployfish.controllers.commands.click.style",
                    side_effect=lambda v, **_: v,
                ):
                    controller.disable()
        command.disable_schedule.assert_called_once()

    def test_run_with_wait_invokes_waiter(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceCommands(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.command = "migrate"
        cement_app.pargs.wait = True
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        invoked = MagicMock()
        invoked.arn = "arn:aws:ecs:us-west-2:123:task/1"
        helper = MagicMock()
        helper.data = {"cluster": "foobar-cluster"}
        helper.run.return_value = [invoked]
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            with patch("deployfish.controllers.commands.get_task", return_value=helper):
                with patch.object(controller, "run_task_waiter") as wait_mock:
                    with patch(
                        "deployfish.controllers.commands.click.style",
                        side_effect=lambda v, **_: v,
                    ):
                        controller.run()
        wait_mock.assert_called_once_with([invoked])


class TestECSServiceCommandLogsGaps:
    def test_list_delegates_to_list_log_streams(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceCommandLogs(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.command = "migrate"
        cement_app.pargs.limit = 10
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        helper = MagicMock()
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            with patch("deployfish.controllers.commands.get_task", return_value=helper):
                with patch(
                    "deployfish.controllers.commands.list_log_streams"
                ) as list_mock:
                    controller.list()
        list_mock.assert_called_once_with(cement_app, helper, limit=10)


class TestLogsControllersGaps:
    def test_log_group_tail_prints_events(self, cement_app: MagicMock) -> None:
        controller = bind_controller(LogsCloudWatchLogGroup(), cement_app)
        cement_app.pargs.name = "/ecs/myapp"
        cement_app.pargs.sleep = 0
        cement_app.pargs.mark = True
        cement_app.pargs.filter_pattern = None
        cement_app.pargs.stream_prefix = "prefix"
        group = CloudWatchLogGroup({"logGroupName": "/ecs/myapp", "arn": "arn:logs:1"})
        event = {
            "timestamp": MagicMock(
                strftime=MagicMock(return_value="2026-01-01 00:00:00.000000")
            ),
            "message": "hello",
        }
        tailer = iter([[event], []])
        loader = MagicMock()
        loader.get_object_from_aws.return_value = group
        controller.loader = MagicMock(return_value=loader)
        with (
            patch(
                "deployfish.controllers.logs.click.style", side_effect=lambda v, **_: v
            ),
            patch.object(group, "get_event_tailer", return_value=tailer),
        ):
            controller.tail()
        assert cement_app.print.call_count >= 2

    def test_log_stream_list_renders(self, cement_app: MagicMock) -> None:
        controller = bind_controller(LogsCloudWatchLogStream(), cement_app)
        cement_app.pargs.log_group_name = "/ecs/myapp"
        cement_app.pargs.prefix = "stream"
        cement_app.pargs.limit = 5
        stream = CloudWatchLogStream(
            {
                "logGroupName": "/ecs/myapp",
                "logStreamName": "stream/abc",
                "creationTime": 1000,
            }
        )
        with patch.object(CloudWatchLogStream.objects, "list", return_value=[stream]):
            controller.list()
        cement_app.print.assert_called_once()

    def test_log_stream_tail_prints_events(self, cement_app: MagicMock) -> None:
        controller = bind_controller(LogsCloudWatchLogStream(), cement_app)
        cement_app.pargs.pk = "/ecs/myapp:stream/abc"
        cement_app.pargs.sleep = 0
        cement_app.pargs.mark = False
        stream = CloudWatchLogStream(
            {
                "logGroupName": "/ecs/myapp",
                "logStreamName": "stream/abc",
            }
        )
        event = {
            "timestamp": MagicMock(
                strftime=MagicMock(return_value="2026-01-01 00:00:00.000000")
            ),
            "message": "line",
        }
        tailer = iter([[event], []])
        loader = MagicMock()
        loader.get_object_from_aws.return_value = stream
        controller.loader = MagicMock(return_value=loader)
        with (
            patch(
                "deployfish.controllers.logs.click.style", side_effect=lambda v, **_: v
            ),
            patch.object(stream, "get_event_tailer", return_value=tailer),
        ):
            controller.tail()
        cement_app.print.assert_called_once()
