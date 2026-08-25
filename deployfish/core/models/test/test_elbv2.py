import logging
import unittest
from unittest.mock import Mock, patch

from deployfish.core.models.elbv2 import (
    LoadBalancerListenerRule,
    LoadBalancerListenerRuleManager,
)

logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)


class TestLoadBalancerListenerRuleManager_get_rules_for_target_group(
    unittest.TestCase
):
    """
    Tests for matching listener rules that forward to a target group,
    including weighted ForwardConfig (canary) layouts.
    """

    TG_ARN_A = (
        "arn:aws:elasticloadbalancing:us-west-2:123456789012:"
        "targetgroup/a/aaaaaaaaaaaaaaaa"
    )
    TG_ARN_B = (
        "arn:aws:elasticloadbalancing:us-west-2:123456789012:"
        "targetgroup/b/bbbbbbbbbbbbbbbb"
    )
    TG_ARN_OTHER = (
        "arn:aws:elasticloadbalancing:us-west-2:123456789012:"
        "targetgroup/other/cccccccccccccccc"
    )
    LB_ARN = (
        "arn:aws:elasticloadbalancing:us-west-2:123456789012:"
        "loadbalancer/app/example/dddddddddddddddd"
    )

    def _rule(self, rule_arn: str, actions: list) -> LoadBalancerListenerRule:
        return LoadBalancerListenerRule(
            {
                "RuleArn": rule_arn,
                "Actions": actions,
                "Conditions": [],
                "Priority": "1",
                "IsDefault": False,
            }
        )

    def _get_rules_for_target_group(
        self,
        rules: list[LoadBalancerListenerRule],
        target_group_arn: str,
    ) -> list[LoadBalancerListenerRule]:
        manager = LoadBalancerListenerRuleManager()
        tg = Mock()
        tg.data = {"LoadBalancerArns": [self.LB_ARN]}
        with patch(
            "deployfish.core.models.elbv2.TargetGroup.objects.get",
            return_value=tg,
        ):
            with patch.object(
                manager,
                "_LoadBalancerListenerRuleManager__get_rules_for_load_balancer",
                return_value=rules,
            ):
                return manager._LoadBalancerListenerRuleManager__get_rules_for_target_group(  # noqa: E501
                    target_group_arn
                )

    def test_matches_single_target_group_arn(self):
        rule = self._rule(
            "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/example/1/aaa",
            [
                {
                    "Type": "forward",
                    "TargetGroupArn": self.TG_ARN_A,
                }
            ],
        )
        matched = self._get_rules_for_target_group([rule], self.TG_ARN_A)
        self.assertEqual(matched, [rule])

    def test_does_not_match_unrelated_single_target_group_arn(self):
        rule = self._rule(
            "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/example/1/aaa",
            [
                {
                    "Type": "forward",
                    "TargetGroupArn": self.TG_ARN_A,
                }
            ],
        )
        matched = self._get_rules_for_target_group([rule], self.TG_ARN_OTHER)
        self.assertEqual(matched, [])

    def test_matches_forward_config_target_groups(self):
        rule = self._rule(
            "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/example/1/bbb",
            [
                {
                    "Type": "forward",
                    "ForwardConfig": {
                        "TargetGroups": [
                            {"TargetGroupArn": self.TG_ARN_A, "Weight": 90},
                            {"TargetGroupArn": self.TG_ARN_B, "Weight": 10},
                        ]
                    },
                }
            ],
        )
        self.assertEqual(
            self._get_rules_for_target_group([rule], self.TG_ARN_A),
            [rule],
        )
        self.assertEqual(
            self._get_rules_for_target_group([rule], self.TG_ARN_B),
            [rule],
        )

    def test_does_not_match_unrelated_forward_config_target_group(self):
        rule = self._rule(
            "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/example/1/bbb",
            [
                {
                    "Type": "forward",
                    "ForwardConfig": {
                        "TargetGroups": [
                            {"TargetGroupArn": self.TG_ARN_A, "Weight": 90},
                            {"TargetGroupArn": self.TG_ARN_B, "Weight": 10},
                        ]
                    },
                }
            ],
        )
        matched = self._get_rules_for_target_group([rule], self.TG_ARN_OTHER)
        self.assertEqual(matched, [])

    def test_ignores_non_forward_actions(self):
        rule = self._rule(
            "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/example/1/ccc",
            [
                {
                    "Type": "redirect",
                    "RedirectConfig": {
                        "Protocol": "HTTPS",
                        "Port": "443",
                        "StatusCode": "HTTP_301",
                    },
                }
            ],
        )
        matched = self._get_rules_for_target_group([rule], self.TG_ARN_A)
        self.assertEqual(matched, [])

    def test_list_by_target_group_arn_uses_matching(self):
        rule = self._rule(
            "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/example/1/ddd",
            [
                {
                    "Type": "forward",
                    "ForwardConfig": {
                        "TargetGroups": [
                            {"TargetGroupArn": self.TG_ARN_A, "Weight": 50},
                            {"TargetGroupArn": self.TG_ARN_B, "Weight": 50},
                        ]
                    },
                }
            ],
        )
        manager = LoadBalancerListenerRuleManager()
        with patch.object(
            manager,
            "_LoadBalancerListenerRuleManager__get_rules_for_target_group",
            return_value=[rule],
        ) as mock_get:
            result = manager.list(target_group_arn=self.TG_ARN_B)
        mock_get.assert_called_once_with(self.TG_ARN_B)
        self.assertEqual(result, [rule])
