from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import WaiterError
from deployfish.core.waiters import HookedWaiter, create_hooked_waiter_with_client
from deployfish.core.waiters.hooks.ecs import ECSTaskStatusHook


class TestHookedWaiter:
    def test_waiter_success_on_first_response(self) -> None:
        config = MagicMock()
        config.acceptors = [MagicMock()]
        config.acceptors[0].matcher_func.return_value = True
        config.acceptors[0].state = "success"
        config.delay = 0
        config.max_attempts = 3
        operation = MagicMock(return_value={"Status": "OK"})
        waiter = HookedWaiter("TestWaiter", config, operation)
        hook = MagicMock()
        waiter.wait(WaiterHooks=[hook])
        hook.assert_called()
        operation.assert_called_once()

    def test_waiter_timeout_raises_waiter_error(self) -> None:
        config = MagicMock()
        acceptor = MagicMock()
        acceptor.matcher_func.return_value = False
        config.acceptors = [acceptor]
        config.delay = 0
        config.max_attempts = 1
        operation = MagicMock(return_value={"Status": "PENDING"})
        waiter = HookedWaiter("TestWaiter", config, operation)
        hook = MagicMock()
        with patch("deployfish.core.waiters.time.sleep"):
            with pytest.raises(WaiterError, match="Max attempts exceeded"):
                waiter.wait(WaiterHooks=[hook])
        assert hook.called


class TestCreateHookedWaiterWithClient:
    def test_waiter_registry_resolves_hook_class(self) -> None:
        client = MagicMock()
        client.meta.events = MagicMock()
        client.meta.service_model = MagicMock()
        waiter_model = MagicMock()
        single_config = MagicMock()
        single_config.operation = "DescribeServices"
        single_config.delay = 1
        single_config.max_attempts = 3
        single_config.acceptors = []
        waiter_model.get_waiter.return_value = single_config
        client.describe_services = MagicMock()
        with patch(
            "deployfish.core.waiters.get_service_module_name",
            return_value="ecs",
        ):
            waiter = create_hooked_waiter_with_client(
                "ServicesStable", waiter_model, client
            )
        assert waiter.name == "ServicesStable"


class TestECSTaskStatusHook:
    def test_ecs_task_status_hook_timeout_message(self) -> None:
        task = MagicMock()
        hook = ECSTaskStatusHook([task])
        with patch("deployfish.core.waiters.hooks.ecs.click.secho") as secho_mock:
            hook.timeout("timeout", {}, 5, cluster="c", tasks=["arn:1"])
        assert "Timed out" in str(secho_mock.call_args)

    def test_ecs_task_status_hook_success_renders_table(self) -> None:
        task = MagicMock()
        task.arn = "arn:aws:ecs:us-west-2:123:task/cluster/abc"
        task.data = {
            "lastStatus": "STOPPED",
            "stopCode": "UserInitiated",
            "stoppedAt": MagicMock(strftime=MagicMock(return_value="2026-01-01")),
        }
        hook = ECSTaskStatusHook([task])
        with patch(
            "deployfish.core.waiters.hooks.ecs.InvokedTask.objects.get",
            return_value=task,
        ):
            with patch("deployfish.core.waiters.hooks.ecs.click.secho"):
                with patch(
                    "deployfish.core.waiters.hooks.ecs.tabulate", return_value="table"
                ):
                    hook.success(
                        "success",
                        {},
                        1,
                        cluster="cluster",
                        tasks=[task.arn],
                    )
