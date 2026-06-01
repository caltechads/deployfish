from datetime import UTC
from unittest.mock import MagicMock, patch

from deployfish.core.waiters.hooks.ecs import ECSDeploymentStatusWaiterHook


class TestECSDeploymentStatusWaiterHook:
    def test_display_deployments_renders_rows(self) -> None:
        hook = ECSDeploymentStatusWaiterHook(MagicMock())
        deployments = [
            {
                "status": "PRIMARY",
                "taskDefinition": "arn:task-def:1",
                "desiredCount": 1,
                "pendingCount": 0,
                "runningCount": 1,
            }
        ]
        with patch("deployfish.core.waiters.hooks.ecs.click.secho") as secho:
            hook.display_deployments(deployments)
        secho.assert_called_once()

    def test_display_events_renders_recent_events(self) -> None:
        from datetime import datetime

        hook = ECSDeploymentStatusWaiterHook(MagicMock())
        now = datetime.now(UTC).astimezone(hook.our_timezone)
        events = [{"createdAt": now, "message": "service stable"}]
        with patch("deployfish.core.waiters.hooks.ecs.click.secho") as secho:
            hook.display_events(events)
        secho.assert_called_once()

    def test_success_prints_message(self) -> None:
        hook = ECSDeploymentStatusWaiterHook(MagicMock())
        with patch("deployfish.core.waiters.hooks.ecs.click.secho") as secho:
            hook.success(None, None, 1)
        assert "stable" in secho.call_args[0][0].lower()
