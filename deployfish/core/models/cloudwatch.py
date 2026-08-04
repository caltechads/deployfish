import contextlib
from collections.abc import Sequence
from typing import Any

from .abstract import Manager, Model

# ----------------------------------------
# Managers
# ----------------------------------------


class CloudwatchAlarmManager(Manager):
    """
    Model cloudwatch alarm manager behavior.
    """

    #: Service.
    service = "cloudwatch"

    def get(self, pk: str, **kwargs) -> "CloudwatchAlarm":  # noqa: ARG002
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            kwargs: kwargs.

        Returns:
            Operation result.

        """
        response = self.client.describe_alarms(AlarmNames=[pk])
        if response.get("MetricAlarms"):
            return CloudwatchAlarm(response["MetricAlarms"][0])
        msg = f'No Cloudwatch Alarm with name "{pk}" exists in AWS'
        raise CloudwatchAlarm.DoesNotExist(msg)

    def list(self, cluster: str, service: str, **kwargs) -> Sequence["CloudwatchAlarm"]:  # noqa: ARG002
        """
        List.

        Args:
            cluster: cluster.
            service: service.

        Keyword Args:
            kwargs: kwargs.

        Returns:
            Operation result.

        """
        response = self.client.describe_alarms(AlarmNamePrefix=[f"{cluster}-{service}"])
        if "MetricAlarms" in response:
            return [CloudwatchAlarm(d) for d in response["MetricAlarms"]]
        return []

    def save(self, obj: Model, **kwargs) -> None:  # noqa: ARG002
        """
        Save.

        Args:
            obj: obj.

        Keyword Args:
            kwargs: kwargs.

        """
        self.delete(obj)
        self.client.put_metric_alarm(**obj.render_for_create())

    def delete(self, obj: Model, **kwargs) -> None:  # noqa: ARG002
        """
        Delete.

        Args:
            obj: obj.

        Keyword Args:
            kwargs: kwargs.

        """
        with contextlib.suppress(self.client.exceptions.ResourceNotFound):
            self.client.delete_alarms(AlarmNames=[obj.pk])


# ----------------------------------------
# Models
# ----------------------------------------


class CloudwatchAlarm(Model):
    """
    Model cloudwatch alarm behavior.
    """

    #: Objects.
    objects = CloudwatchAlarmManager()

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.

        """
        return self.data["AlarmName"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.

        """
        return self.data["AlarmName"]

    @property
    def arn(self) -> str:
        """
        Arn.

        Returns:
            Operation result.

        """
        return self.data.get("AlarmArn", None)

    def set_policy_arn(self, arn: str) -> None:
        """
        Set policy arn.

        Args:
            arn: arn.

        """
        self.data["AlarmActions"] = [arn]

    def render_for_diff(self) -> dict[str, Any]:
        """
        Render for diff.

        Returns:
            Operation result.

        """
        data = {}
        data["AlarmName"] = self.data["AlarmName"]
        data["AlarmDescription"] = self.data["AlarmDescription"]
        data["MetricName"] = self.data["MetricName"]
        data["Namespace"] = self.data["Namespace"]
        data["Statistic"] = self.data["Statistic"]
        data["Dimensions"] = self.data["Dimensions"]
        data["Period"] = self.data["Period"]
        data["Unit"] = self.data["Unit"]
        data["EvaluationPeriods"] = self.data["EvaluationPeriods"]
        data["ComparisonOperator"] = self.data["ComparisonOperator"]
        data["Threshold"] = self.data["Threshold"]
        return data
