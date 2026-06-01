from unittest.mock import MagicMock, patch

import pytest
from deployfish.core.models.appscaling import ScalableTarget, ScalingPolicy
from deployfish.core.models.cloudwatch import CloudwatchAlarm

POLICY_DATA = {
    "PolicyName": "scale-up",
    "PolicyARN": "arn:aws:autoscaling:us-west-2:123:scalingPolicy:1",
    "ServiceNamespace": "ecs",
    "ResourceId": "service/cluster/service",
    "ScalableDimension": "ecs:service:DesiredCount",
    "PolicyType": "StepScaling",
    "Alarms": [{"AlarmName": "cpu-high"}],
}

TARGET_DATA = {
    "ResourceId": "service/cluster/service",
    "ScalableDimension": "ecs:service:DesiredCount",
    "MinCapacity": 1,
    "MaxCapacity": 4,
    "RoleARN": "arn:aws:iam::123:role/as",
    "ServiceNamespace": "ecs",
}


class TestScalingPolicyManager:
    def test_get_policy(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_scaling_policies.return_value = {
            "ScalingPolicies": [POLICY_DATA]
        }
        alarm = MagicMock()
        with patch.object(CloudwatchAlarm.objects, "get", return_value=alarm):
            policy = ScalingPolicy.objects.get("scale-up")
        assert policy.pk == "scale-up"

    def test_get_raises_when_missing(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_scaling_policies.return_value = {"ScalingPolicies": []}
        with pytest.raises(ScalingPolicy.DoesNotExist):
            ScalingPolicy.objects.get("missing")

    def test_list_policies(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_scaling_policies.return_value = {
            "ScalingPolicies": [POLICY_DATA]
        }
        with patch.object(CloudwatchAlarm.objects, "get", return_value=MagicMock()):
            policies = ScalingPolicy.objects.list("cluster", "service")
        assert len(policies) == 1

    def test_delete_policy(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        policy = ScalingPolicy(POLICY_DATA, alarm=None)
        ScalingPolicy.objects.delete(policy)
        client.delete_scaling_policy.assert_called_once()


class TestScalableTargetManager:
    def test_get_target(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_scalable_targets.return_value = {
            "ScalableTargets": [TARGET_DATA]
        }
        with patch.object(ScalingPolicy.objects, "list", return_value=[]):
            ScalableTarget.objects.get("service/cluster/service")

    def test_save_registers_target(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.register_scalable_target.return_value = {}
        target = ScalableTarget(TARGET_DATA, policies=[])
        with patch.object(ScalableTarget.objects, "exists", return_value=False):
            ScalableTarget.objects.save(target)
        client.register_scalable_target.assert_called_once()
