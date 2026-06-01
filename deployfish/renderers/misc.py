from deployfish.core.models import TargetGroup


def target_group_listener_rules(obj: TargetGroup) -> str:
    """
    Return listener-rule summaries for one target group.

    Args:
        obj: Target group to summarize.

    Returns:
        Newline-joined listener rule descriptions.

    """
    rules = obj.rules
    conditions: list[str] = []
    for rule in rules:
        if "Conditions" in rule.data:
            for condition in rule.data["Conditions"]:
                if "HostHeaderConfig" in condition:
                    conditions.extend(
                        f"hostname:{value}"
                        for value in condition["HostHeaderConfig"]["Values"]
                    )
                if "HttpHeaderConfig" in condition:
                    conditions.append(
                        "header:{} -> {}".format(
                            condition["HttpHeaderConfig"]["HttpHeaderName"],
                            ",".join(condition["HttpHeaderConfig"]["Values"]),
                        )
                    )
                if "PathPatternConfig" in condition:
                    conditions.extend(
                        f"path:{value}"
                        for value in condition["PathPatternConfig"]["Values"]
                    )
                if "QueryStringConfig" in condition:
                    conditions.extend(
                        "qs:{}={} -> ".format(value["Key"], value["Value"])
                        for value in condition["QueryStringConfig"]["Values"]
                    )
                if "SourceIpConfig" in condition:
                    conditions.extend(
                        f"ip:{value} -> "
                        for value in condition["SourceIpConfig"]["Values"]
                    )
                if "HttpRequestMethod" in condition:
                    conditions.extend(
                        f"verb:{value} -> "
                        for value in condition["HttpRequestMethod"]["Values"]
                    )
    if not conditions:
        conditions.append(
            "forward:"
            f"{obj.load_balancers[0].lb_type}:{obj.listeners[0].port}:"
            f"{obj.listeners[0].protocol} -> CONTAINER:{obj.port}:{obj.protocol}"
        )
    return "\n".join(sorted(conditions))
