"""AutoscalingGroup model coverage."""

from unittest.mock import patch

import pytest
from deployfish.core.models.ec2 import AutoscalingGroup


class TestAutoscalingGroupScale:
    ASG_DATA = {
        "AutoScalingGroupName": "ecs-asg",
        "MinSize": 2,
        "MaxSize": 10,
        "DesiredCapacity": 4,
        "Instances": [],
    }

    def test_scale_within_bounds(self) -> None:
        asg = AutoscalingGroup(self.ASG_DATA)
        with patch.object(AutoscalingGroup.objects, "exists", return_value=True):
            with patch.object(asg, "save") as save_mock:
                asg.scale(5, force=False)
        save_mock.assert_called_once()
        assert asg.data["DesiredCapacity"] == 5

    def test_scale_force_expands_max(self) -> None:
        asg = AutoscalingGroup(self.ASG_DATA)
        with patch.object(AutoscalingGroup.objects, "exists", return_value=True):
            with patch.object(asg, "save"):
                asg.scale(15, force=True)
        assert asg.data["MaxSize"] == 15
        assert asg.data["DesiredCapacity"] == 15

    def test_scale_raises_below_min_without_force(self) -> None:
        asg = AutoscalingGroup(self.ASG_DATA)
        with patch.object(AutoscalingGroup.objects, "exists", return_value=True):
            with pytest.raises(AutoscalingGroup.OperationFailed):
                asg.scale(1, force=False)

    def test_scale_raises_when_asg_missing(self) -> None:
        asg = AutoscalingGroup(self.ASG_DATA)
        with patch.object(AutoscalingGroup.objects, "exists", return_value=False):
            with pytest.raises(AutoscalingGroup.DoesNotExist):
                asg.scale(3)
