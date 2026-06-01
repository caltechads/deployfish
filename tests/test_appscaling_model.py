from unittest.mock import patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.appscaling import ScalableTarget, ScalingPolicy

from tests.fixtures import APPLICATION_SCALING_YML


class TestScalableTargetModel:
    def test_new_from_application_scaling_yaml(self) -> None:
        target = ScalableTarget.new(
            APPLICATION_SCALING_YML,
            "deployfish",
            cluster="my-cluster",
            service="my-service",
        )
        assert target.data["ResourceId"] == "service/my-cluster/my-service"
        assert target.data["MinCapacity"] == 2
        assert len(target.policies) == 2

    def test_save_registers_target_and_policies(self) -> None:
        target = ScalableTarget.new(
            APPLICATION_SCALING_YML,
            "deployfish",
            cluster="my-cluster",
            service="my-service",
        )
        with patch.object(ScalableTarget.objects, "save") as save_mock:
            target.save()
        save_mock.assert_called_once_with(target)

    def test_delete_deregisters_target(self) -> None:
        target = ScalableTarget.new(
            APPLICATION_SCALING_YML,
            "deployfish",
            cluster="my-cluster",
            service="my-service",
        )
        with patch.object(ScalableTarget.objects, "delete") as delete_mock:
            target.delete()
        delete_mock.assert_called_once_with(target)


class TestScalingPolicyModel:
    def test_save_puts_scaling_policy(self) -> None:
        policy = ScalingPolicy.new(
            APPLICATION_SCALING_YML["scale-up"],
            "deployfish",
            cluster="my-cluster",
            service="my-service",
        )
        with patch.object(
            ScalingPolicy.objects, "save", return_value="arn:policy:1"
        ) as save_mock:
            arn = policy.save()
        save_mock.assert_called_once_with(policy)
        assert arn == "arn:policy:1"
