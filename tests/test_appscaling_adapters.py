import deployfish.core.adapters  # noqa: F401
from deployfish.core.adapters.deployfish.appscaling import (
    ECSServiceScalableTargetAdapter,
    ECSServiceScalingPolicyAdapter,
)


class TestECSServiceScalingPolicyAdapter:
    def test_scale_up_policy_name(self) -> None:
        adapter = ECSServiceScalingPolicyAdapter(
            {
                "cpu": ">=60",
                "check_every_seconds": 60,
                "periods": 5,
                "cooldown": 60,
                "scale_by": 1,
            },
            cluster="my-cluster",
            service="my-service",
        )
        data, kwargs = adapter.convert()
        assert data["PolicyName"] == "my-cluster-my-service-scale-up"
        assert data["ResourceId"] == "service/my-cluster/my-service"
        assert data["ScalableDimension"] == "ecs:service:DesiredCount"
        assert (
            data["StepScalingPolicyConfiguration"]["StepAdjustments"][0][
                "ScalingAdjustment"
            ]
            == 1
        )
        assert (
            data["StepScalingPolicyConfiguration"]["StepAdjustments"][0][
                "MetricIntervalLowerBound"
            ]
            == 0.0
        )
        assert "alarm" in kwargs

    def test_scale_down_policy_name(self) -> None:
        adapter = ECSServiceScalingPolicyAdapter(
            {
                "cpu": "<=30",
                "check_every_seconds": 60,
                "periods": 30,
                "cooldown": 60,
                "scale_by": -1,
            },
            cluster="my-cluster",
            service="my-service",
        )
        data, _kwargs = adapter.convert()
        assert data["PolicyName"] == "my-cluster-my-service-scale-down"
        assert (
            data["StepScalingPolicyConfiguration"]["StepAdjustments"][0][
                "MetricIntervalUpperBound"
            ]
            == 0.0
        )


class TestECSServiceScalableTargetAdapter:
    def test_convert_builds_target_and_policies(self) -> None:
        adapter = ECSServiceScalableTargetAdapter(
            {
                "min_capacity": 2,
                "max_capacity": 4,
                "role_arn": "arn:aws:iam::123:role/scaling",
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
                    "periods": 30,
                    "cooldown": 60,
                    "scale_by": -1,
                },
            },
            cluster="my-cluster",
            service="my-service",
        )
        data, kwargs = adapter.convert()
        assert data["ResourceId"] == "service/my-cluster/my-service"
        assert data["MinCapacity"] == 2
        assert data["MaxCapacity"] == 4
        assert data["RoleARN"] == "arn:aws:iam::123:role/scaling"
        assert len(kwargs["policies"]) == 2
        policy_names = {p.pk for p in kwargs["policies"]}
        assert policy_names == {
            "my-cluster-my-service-scale-up",
            "my-cluster-my-service-scale-down",
        }
