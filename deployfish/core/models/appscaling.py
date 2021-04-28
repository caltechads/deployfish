from .abstract import Manager, Model
from .cloudwatch import CloudwatchAlarm


# ----------------------------------------
# Managers
# ----------------------------------------

class ScalingPolicyManager(Manager):

    service = 'application-autoscaling'

    def get(self, pk, **kwargs):
        response = self.client.describe_scaling_policies(PolicyNames=[pk], ServiceNamespace='ecs')
        if 'ScalingPolicies' in response and response['ScalingPolicies']:
            data = response['ScalingPolicies'][0]
        else:
            raise ScalingPolicy.DoesNotExist('No ScalingPolicy with name "{}" exists in AWS'.format(pk))
        if 'Alarms' in data and data['Alarms']:
            alarm = CloudwatchAlarm.objects.get(data['Alarms'][0]['AlarmName'])
        else:
            alarm = None
        return ScalingPolicy(data, alarm=alarm)

    def list(self, cluster, service):
        response = self.client.describe_scaling_policies(
            ServiceNamespace='ecs',
            ResourceId='service/{}/{}'.format(cluster, service)
        )
        policies = []
        for data in response['ScalingPolicies']:
            if 'Alarms' in data and data['Alarms']:
                alarm = CloudwatchAlarm.objects.get(data['Alarms'][0]['AlarmName'])
            else:
                alarm = None
            policies.append(ScalingPolicy(data, alarm=alarm))
        return policies

    def save(self, obj):
        # NOTE: even though the operation is called put_scaling_policy, it can be used for both create
        # and update.  Thus we don't need to remove the existing ScalableTarget if we want to update it
        # See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/application-autoscaling.html#ApplicationAutoScaling.Client.put_scaling_policy
        response = self.client.put_scaling_policy(**obj.render_for_create())
        arn = response['PolicyARN']
        self.alarm.set_policy_arn(arn)
        self.alarm.save()
        return arn

    def delete(self, obj):
        if obj.alarm:
            obj.alarm.delete()
        try:
            self.client.delete_scaling_policy(
                PolicyName=obj.pk,
                ServiceNamespace=obj.data['ServiceNamespace'],
                ResourceId=obj.data['ResourceId'],
                ScalableDimension=obj.data['ScalableDimension']
            )
        except self.client.ObjectNotFoundException:
            pass


class ScalableTargetManager(Manager):

    service = 'application-autoscaling'

    def get(self, pk, **kwargs):
        response = self.client.describe_scalable_targets(
            ResourceIds=[pk],
            ServiceNamespace='ecs'
        )
        _, cluster, service = pk.split('/')
        if 'ScalableTargets' in response and response['ScalableTargets']:
            data = response['ScalableTargets'][0]
        else:
            raise ScalableTarget.DoesNotExist('No ScalableTarget with name "{}" exists in AWS'.format(pk))
        policies = ScalingPolicy.objects.list(cluster, service)
        return ScalableTarget(data, policies=policies)

    def list(self):
        response = self.client.describe_scalable_targets(
            ServiceNamespace='ecs',
            ScalableDimension='ecs:service:DesiredCount'
        )
        targets = []
        for data in response['ScalableTargets']:
            _, cluster, service = data['ResourceId'].split('/')
            policies = ScalingPolicy.objects.list(cluster, service)
            targets.append(ScalingPolicy(data, policies=policies))
        return targets

    def save(self, obj):
        # NOTE: even though the operation is called register_scalable_target, it can be used for both create
        # and update.  Thus we don't need to remove the existing ScalableTarget if we want to update it
        # See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/application-autoscaling.html#ApplicationAutoScaling.Client.register_scalable_target
        self.client.register_scalable_target(**obj.render_for_create())
        for policy in obj.policies:
            policy.save()

    def delete(self, obj):
        for policy in obj.policies:
            policy.delete()
        try:
            self.client.deregister_scalable_target(
                ServiceNamespace=obj.data['ServiceNamespace'],
                ResourceId=obj.pk,
                ScalableDimension=obj.data['ScalableDimension']
            )
        except self.client.ObjectNotFoundException:
            pass


# ----------------------------------------
# Models
# ----------------------------------------

class ScalingPolicy(Model):

    objects = ScalingPolicyManager()

    def __init__(self, data, alarm=None):
        super(ScalingPolicy, self).__init__(data)
        self.alarm = alarm

    @property
    def pk(self):
        return self.data['PolicyName']

    @property
    def name(self):
        return self.data['PolicyName']

    @property
    def arn(self):
        return self.data.get('PolicyARN', None)

    def render_for_diff(self):
        data = self.render()
        if 'PolicyARN' in data:
            del data['PolicyARN']
            del data['CreationTime']
            del data['Alarms']
        if self.alarm:
            data['alarm'] = self.alarm.render_for_diff()
        return data


class ScalableTarget(Model):

    objects = ScalableTargetManager()

    def __init__(self, data, policies=None):
        super(ScalableTarget, self).__init__(data)
        if not policies:
            policies = []
        self.policies = policies

    @property
    def pk(self):
        return self.data['ResourceId']

    @property
    def name(self):
        return self.data['ResourceId']

    def render_for_diff(self):
        data = self.render()
        # RoleARN gets set however AWS wants it instead of what we tell it, so ignore that for comparison
        del data['RoleARN']
        if 'CreationTime' in data:
            del data['CreationTime']
        else:
            data['SuspendedState'] = {
                'DynamicScalingInSuspended': False,
                'DynamicScalingOutSuspended': False,
                'ScheduledScalingSuspended': False
            }
        data['scaling_policies'] = [p.render_for_diff() for p in sorted(self.policies, key=lambda x: x.pk)]
        return data
