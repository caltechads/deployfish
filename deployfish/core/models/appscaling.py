import contextlib
from collections.abc import Sequence
from typing import Any, cast

from .abstract import Manager, Model
from .cloudwatch import CloudwatchAlarm

__all__ = ["ScalableTarget", "ScalingPolicy"]


# ----------------------------------------
# Managers
# ----------------------------------------


class ScalingPolicyManager(Manager):
    service = "application-autoscaling"

    def get(self, pk: str, **_) -> "ScalingPolicy":
        response = self.client.describe_scaling_policies(
            PolicyNames=[pk], ServiceNamespace="ecs"
        )
        if response.get("ScalingPolicies"):
            data = response["ScalingPolicies"][0]
        else:
            msg = f'No ScalingPolicy with name "{pk}" exists in AWS'
            raise ScalingPolicy.DoesNotExist(msg)
        if data.get("Alarms"):
            alarm = CloudwatchAlarm.objects.get(data["Alarms"][0]["AlarmName"])
        else:
            alarm = None
        return ScalingPolicy(data, alarm=alarm)

    def list(self, cluster, service):
        response = self.client.describe_scaling_policies(
            ServiceNamespace="ecs", ResourceId=f"service/{cluster}/{service}"
        )
        policies = []
        for data in response["ScalingPolicies"]:
            if data.get("Alarms"):
                alarm = CloudwatchAlarm.objects.get(data["Alarms"][0]["AlarmName"])
            else:
                alarm = None
            policies.append(ScalingPolicy(data, alarm=alarm))
        return policies

    def save(self, obj: Model, **_) -> str:
        # put_scaling_policy handles both create and update for existing policy.
        obj = cast("ScalingPolicy", obj)
        response = self.client.put_scaling_policy(**obj.render_for_create())
        arn = response["PolicyARN"]
        if obj.alarm:
            obj.alarm.set_policy_arn(arn)
            obj.alarm.save()
        return arn

    def delete(self, obj: Model, **_) -> None:
        obj = cast("ScalingPolicy", obj)
        if obj.alarm:
            obj.alarm.delete()
        with contextlib.suppress(self.client.exceptions.ObjectNotFoundException):
            self.client.delete_scaling_policy(
                PolicyName=obj.pk,
                ServiceNamespace=obj.data["ServiceNamespace"],
                ResourceId=obj.data["ResourceId"],
                ScalableDimension=obj.data["ScalableDimension"],
            )


class ScalableTargetManager(Manager):
    service = "application-autoscaling"

    def get(self, pk: str, **_) -> "ScalableTarget":
        """
        Get a single ScalableTarget.
        """
        response = self.client.describe_scalable_targets(
            ResourceIds=[pk], ServiceNamespace="ecs"
        )
        _resource_type, cluster, service_name = pk.split("/")
        if response.get("ScalableTargets"):
            data = response["ScalableTargets"][0]
        else:
            msg = f'No ScalableTarget with name "{pk}" exists in AWS'
            raise ScalableTarget.DoesNotExist(msg)
        policies = ScalingPolicy.objects.list(cluster, service_name)
        return ScalableTarget(data, policies=policies)

    def list(self) -> Sequence["ScalableTarget"]:
        response = self.client.describe_scalable_targets(
            ServiceNamespace="ecs", ScalableDimension="ecs:service:DesiredCount"
        )
        targets = []
        for data in response["ScalableTargets"]:
            _resource_type, cluster, service_name = data["ResourceId"].split("/")
            policies = ScalingPolicy.objects.list(cluster, service_name)
            targets.append(ScalableTarget(data, policies=policies))
        return targets

    def save(self, obj: Model, **_) -> None:
        # register_scalable_target handles both create and update for target.
        obj = cast("ScalableTarget", obj)
        self.client.register_scalable_target(**obj.render_for_create())
        for policy in obj.policies:
            policy.save()

    def delete(self, obj: Model, **_) -> None:
        obj = cast("ScalableTarget", obj)
        for policy in obj.policies:
            policy.delete()
        with contextlib.suppress(self.client.exceptions.ObjectNotFoundException):
            self.client.deregister_scalable_target(
                ServiceNamespace=obj.data["ServiceNamespace"],
                ResourceId=obj.pk,
                ScalableDimension=obj.data["ScalableDimension"],
            )


# ----------------------------------------
# Models
# ----------------------------------------


class ScalingPolicy(Model):
    #: Manager for Application Auto Scaling policy records.
    objects = ScalingPolicyManager()

    def __init__(
        self, data: dict[str, Any], alarm: CloudwatchAlarm | None = None
    ) -> None:
        super().__init__(data)
        #: Alarm attached to this scaling policy, if AWS configured one.
        self.alarm: CloudwatchAlarm | None = alarm

    @property
    def pk(self) -> str:
        return self.data["PolicyName"]

    @property
    def name(self) -> str:
        return self.data["PolicyName"]

    @property
    def arn(self) -> str:
        return self.data.get("PolicyARN", None)

    def render_for_diff(self) -> dict[str, Any]:
        data = self.render()
        if "PolicyARN" in data:
            del data["PolicyARN"]
            del data["CreationTime"]
            del data["Alarms"]
        if self.alarm:
            data["alarm"] = self.alarm.render_for_diff()
        return data


class ScalableTarget(Model):
    #: Manager for scalable target records.
    objects = ScalableTargetManager()

    def __init__(
        self, data: dict[str, Any], policies: Sequence[ScalingPolicy] | None = None
    ) -> None:
        super().__init__(data)
        if not policies:
            policies = []
        #: Scaling policies attached to this target.
        self.policies: Sequence[ScalingPolicy] = policies

    @property
    def pk(self) -> str:
        return self.data["ResourceId"]

    @property
    def name(self) -> str:
        return self.data["ResourceId"]

    def render_for_diff(self) -> dict[str, Any]:
        data = self.render()
        # AWS rewrites RoleARN, so ignore it during comparisons.
        del data["RoleARN"]
        if "CreationTime" in data:
            del data["CreationTime"]
        else:
            data["SuspendedState"] = {
                "DynamicScalingInSuspended": False,
                "DynamicScalingOutSuspended": False,
                "ScheduledScalingSuspended": False,
            }
        data["scaling_policies"] = [
            p.render_for_diff() for p in sorted(self.policies, key=lambda x: x.pk)
        ]
        if "ScalableTargetARN" in data:
            del data["ScalableTargetARN"]
        return data

    def render_for_create(self) -> dict[str, Any]:
        data = self.render()
        if "CreationTime" in data:
            del data["CreationTime"]
        return data
