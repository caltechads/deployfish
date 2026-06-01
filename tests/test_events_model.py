from unittest.mock import MagicMock, patch

import pytest
from deployfish.core.models.events import EventScheduleRule, EventTarget

RULE_DATA = {
    "Name": "deployfish-foobar-test-mytask",
    "Arn": "arn:aws:events:us-west-2:123:rule/deployfish-foobar-test-mytask",
    "State": "ENABLED",
    "ScheduleExpression": "rate(1 day)",
    "EventBusName": "default",
}

TARGET_DATA = {
    "Id": "deployfish-foobar-test-mytask",
    "Arn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
    "RoleArn": "arn:aws:iam::123:role/events",
    "EcsParameters": {
        "TaskDefinitionArn": "arn:aws:ecs:us-west-2:123:task-definition/td:1",
        "TaskCount": 1,
    },
}


class TestEventTargetManager:
    def test_get_returns_target(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.list_targets_by_rule.return_value = {"Targets": [TARGET_DATA]}
        rule = EventScheduleRule(RULE_DATA)
        target = EventTarget.objects.get(TARGET_DATA["Id"], rule=rule)
        assert target.pk == TARGET_DATA["Id"]

    def test_get_raises_when_missing(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.list_targets_by_rule.return_value = {"Targets": []}
        rule = EventScheduleRule(RULE_DATA)
        with pytest.raises(EventTarget.DoesNotExist):
            EventTarget.objects.get("missing", rule=rule)

    def test_save_puts_targets(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        rule = EventScheduleRule(RULE_DATA)
        target = EventTarget(TARGET_DATA, rule=rule)
        with patch.object(target, "render", return_value=TARGET_DATA):
            EventTarget.objects.save(target)
        client.put_targets.assert_called_once()

    def test_delete_removes_targets(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        rule = EventScheduleRule(RULE_DATA)
        target = EventTarget(TARGET_DATA, rule=rule)
        EventTarget.objects.delete(target)
        client.remove_targets.assert_called_once()


class TestEventScheduleRuleManager:
    def test_get_prefixes_deployfish_name(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.list_rules.return_value = {"Rules": [RULE_DATA]}
        client.list_targets_by_rule.return_value = {"Targets": [TARGET_DATA]}
        rule = EventScheduleRule.objects.get("foobar-test-mytask")
        assert rule.pk == RULE_DATA["Name"]

    def test_get_raises_when_missing(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.list_rules.return_value = {"Rules": []}
        with pytest.raises(EventScheduleRule.DoesNotExist):
            EventScheduleRule.objects.get("missing-task")

    def test_enable_sets_state(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        disabled = {**RULE_DATA, "State": "DISABLED"}
        rule = EventScheduleRule(disabled)
        EventScheduleRule.objects.enable(rule)
        client.enable_rule.assert_called_once_with(
            Name=rule.name,
            EventBusName=rule.data["EventBusName"],
        )

    def test_disable_sets_state(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        rule = EventScheduleRule(RULE_DATA)
        EventScheduleRule.objects.disable(rule)
        client.disable_rule.assert_called_once_with(
            Name=rule.name,
            EventBusName=rule.data["EventBusName"],
        )
