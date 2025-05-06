from deployfish.core.models import TargetGroup


def target_group_listener_rules(obj: TargetGroup) -> str:
    """
    Given a ``TargetGroup`` iterate through its list of LoadBalancerListenerRule objects and return a human readable
    description of those rules.

    :param obj TargetGroup: a TargetGroup object

    :rtype: str
    """
    rules = obj.rules
    conditions = []
    for rule in rules:
        if "Conditions" in rule.data:
            for condition in rule.data["Conditions"]:
                if "HostHeaderConfig" in condition:
                    for v in condition["HostHeaderConfig"]["Values"]:
                        conditions.append(f"hostname:{v}")
                if "HttpHeaderConfig" in condition:
                    conditions.append("header:{} -> {}".format(
                        condition["HttpHeaderConfig"]["HttpHeaderName"],
                        ",".join(condition["HttpHeaderConfig"]["Values"])
                    ))
                if "PathPatternConfig" in condition:
                    for v in condition["PathPatternConfig"]["Values"]:
                        conditions.append(f"path:{v}")
                if "QueryStringConfig" in condition:
                    for v in condition["QueryStringConfig"]["Values"]:
                        conditions.append("qs:{}={} -> ".format(v["Key"], v["Value"]))
                if "SourceIpConfig" in condition:
                    for v in condition["SourceIpConfig"]["Values"]:
                        conditions.append(f"ip:{v} -> ")
                if "HttpRequestMethod" in condition:
                    for v in condition["HttpRequestMethod"]["Values"]:
                        conditions.append(f"verb:{v} -> ")
    if not conditions:
        conditions.append(f"forward:{obj.load_balancers[0].lb_type}:{obj.listeners[0].port}:{obj.listeners[0].protocol} -> CONTAINER:{obj.port}:{obj.protocol}")
    return "\n".join(sorted(conditions))
