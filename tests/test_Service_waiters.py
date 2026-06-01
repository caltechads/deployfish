from unittest.mock import MagicMock, patch

from deployfish.core.models.ecs import Service
from deployfish.core.waiters.hooks.ecs import ECSDeploymentStatusWaiterHook


class TestECSDeploymentStatusWaiterHook:
    def test_success_prints_stable_message(self, capsys) -> None:
        service = MagicMock(spec=Service)
        service.deployments = []
        service.events = []
        hook = ECSDeploymentStatusWaiterHook(service)
        with patch("deployfish.core.waiters.hooks.ecs.click.secho") as secho_mock:
            hook.success("success", {}, 1, cluster="c", services=["svc"])
        secho_mock.assert_called()
        assert "stable" in str(secho_mock.call_args).lower()

    def test_failure_prints_failure_message(self) -> None:
        service = MagicMock(spec=Service)
        hook = ECSDeploymentStatusWaiterHook(service)
        with patch("deployfish.core.waiters.hooks.ecs.click.secho") as secho_mock:
            hook.failure("failure", {}, 1, cluster="c", services=["svc"])
        assert "failed" in str(secho_mock.call_args).lower()

    def test_waiting_displays_deployments(self) -> None:
        service = MagicMock(spec=Service)
        service.deployments = [
            {
                "status": "PRIMARY",
                "taskDefinition": "arn:task:1",
                "desiredCount": 1,
                "pendingCount": 0,
                "runningCount": 1,
            }
        ]
        service.events = []
        hook = ECSDeploymentStatusWaiterHook(service)
        with (
            patch(
                "deployfish.core.waiters.hooks.ecs.Service.objects.get",
                return_value=service,
            ),
            patch.object(hook, "display_deployments") as display_mock,
            patch.object(hook, "display_events"),
            patch.object(hook, "mark"),
        ):
            hook.waiting("running", {}, 1, cluster="c", services=["svc"])
        display_mock.assert_called_once_with(service.deployments)
