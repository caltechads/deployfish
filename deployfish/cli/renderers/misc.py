def target_group_listener_rules(obj):
    """
    Given a ``TargetGroup`` iterate through its list of LoadBalancerListenerRule objects and return a human readable
    description of those rules.

    :param obj TargetGroup: a TargetGroup object

    :rtype: str
    """
    rules = obj.rules
    conditions = []
    for rule in rules:
        if 'Conditions' in rule.data:
            for condition in rule.data['Conditions']:
                if 'HostHeaderConfig' in condition:
                    for v in condition['HostHeaderConfig']['Values']:
                        conditions.append('hostname:{}'.format(v))
                if 'HttpHeaderConfig' in condition:
                    conditions.append('header:{} -> {}'.format(
                        condition['HttpHeaderConfig']['HttpHeaderName'],
                        ','.join(condition['HttpHeaderConfig']['Values'])
                    ))
                if 'PathPatternConfig' in condition:
                    for v in condition['PathPatternConfig']['Values']:
                        conditions.append('path:{}'.format(v))
                if 'QueryStringConfig' in condition:
                    for v in condition['QueryStringConfig']['Values']:
                        conditions.append('qs:{} -> '.format(v['Key'], v['Value']))
                if 'SourceIpConfig' in condition:
                    for v in condition['SourceIpConfig']['Values']:
                        conditions.append('ip:{} -> '.format(v))
                if 'HttpRequestMethod' in condition:
                    for v in condition['HttpRequestMethod']['Values']:
                        conditions.append('verb:{} -> '.format(v))
    if not conditions:
        conditions.append('forward:ALB:{} -> CONTAINER:{}'.format(obj.listeners[0].port, obj.port))
    return '\n'.join(sorted(conditions))
