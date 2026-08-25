Application/Network Load Balancing
==================================

Models and managers for Application Load Balancers (ALB) and Network Load
Balancers (NLB), including listeners, listener rules, and target groups.

Weighted and canary target groups
---------------------------------

When an ALB listener rule uses weighted forwarding (for example canary
deployments), AWS stores the target groups under
``Actions[].ForwardConfig.TargetGroups`` instead of a single top-level
``TargetGroupArn``.

:py:meth:`deployfish.core.models.elbv2.LoadBalancerListenerRuleManager.list`
with ``target_group_arn=...``, and therefore
:py:attr:`deployfish.core.models.elbv2.TargetGroup.rules`, match rules that
reference a target group in either form.

.. automodule:: deployfish.core.models.elbv2
    :members:
    :undoc-members:
    :show-inheritance:
