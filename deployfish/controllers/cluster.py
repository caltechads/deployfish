import argparse
from datetime import UTC, datetime
from typing import Any, cast

import click
from cement import ex

from deployfish.core.models import (
    AutoscalingGroup,
    Cluster,
    Model,
)
from deployfish.renderers.table import TableRenderer

from ..exceptions import ObjectDoesNotExist
from .crud import CrudBase
from .network import ObjectSSHController
from .utils import handle_model_exceptions


def valid_date(s):
    """
    Parse a date string in the form YYYY-MM-DD and return a datetime.

    Args:
        s: s.

    Returns:
        Operation result.

    """
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        msg = f"not a valid date: {s!r}"
        raise argparse.ArgumentTypeError(msg) from None


class ECSCluster(CrudBase):
    """
    Model ecscluster behavior.
    """

    class Meta:
        label = "cluster"
        description = "Work with ECS Cluster objects"
        help = "Work with ECS Cluster objects"
        stacked_type = "nested"

    #: Model.
    model: type[Model] = Cluster
    #: Help overrides.
    help_overrides: dict[str, str] = {
        "info": "Show details about an ECS Cluster object from AWS",
    }

    # .info() related vars

    #: Info template.
    info_template: str = "detail--cluster.jinja2"

    # .list() related vars

    #: List ordering.
    list_ordering: str | None = "Name"
    #: List result columns.
    list_result_columns: dict[str, Any] = {
        "Name": "clusterName",
        "Type": "cluster_type",
        "Instances": "registeredContainerInstancesCount",
        "Services": "activeServicesCount",
        "Running Tasks": "runningTasksCount",
        "Pending Tasks": "pendingTasksCount",
    }

    def _scale_instances(self, obj: Cluster, count: int, force: bool) -> None:  # noqa: FBT001
        """
        Scale the number of instances in an ECS Cluster to match ``count``.

        .. warning::

            This only works if ``Cluster.autoscaling_group`` is defined.

        Args:
            obj: the cluster to work on
            count: set the number of instances in the cluster to this
            force: If ``True`` and ``count`` is more then MaxSize or less than MinSize,
            force
                   the autoscaling group to change its MinSize or MaxSize also

        Raises:
            ObjectDoesNotExist: if ``Cluster.autoscaling_group`` is ``None``
            AutoscalingGroup.OperationFailed: if ``count`` is outside MinSize/MaxSize
            and ``force`` is ``False``

        """
        if obj.autoscaling_group is None:
            msg = f"Cluster(pk={obj.pk}) has no autoscaling group to scale"
            raise ObjectDoesNotExist(msg)
        try:
            obj.scale(count, force=force)
        except AutoscalingGroup.OperationFailed as e:
            msg = str(e)
            asg = cast("AutoscalingGroup", obj.autoscaling_group)
            if "MinSize" in msg:
                lines = []
                lines.append(
                    'Desired count {} is less than MinSize of {} on AutoscalingGroup "{}".'.format(  # noqa: E501
                        count, asg.data["MinSize"], asg.name
                    )
                )
                lines.append("\nEither:")
                lines.append(
                    f"  (1) use --force to also reduce AutoscalingGroup MinSize to {count}"  # noqa: E501
                )
                lines.append("  (2) specify count >= {}".format(asg.data["MinSize"]))
            else:
                lines = []
                lines.append(
                    'Desired count {} is greater than MaxSize of {} on AutoscalingGroup "{}".'.format(  # noqa: E501
                        count, asg.data["MaxSize"], asg.name
                    )
                )
                lines.append("\nEither:")
                lines.append(
                    f"  (1) use --force to also increase AutoscalingGroup MaxSize to {count}"  # noqa: E501
                )
                lines.append(
                    "  (2) specify count <= {}".format(
                        obj.autoscaling_group.data["MaxSize"]
                    )
                )
            raise AutoscalingGroup.OperationFailed("\n".join(lines)) from e
        self.app.print(
            click.style(
                f'Set count for Cluster("{obj.pk}") to {count} instances.', fg="green"
            )
        )

    @ex(
        help="List ECS Clusters from AWS",
        arguments=[
            (
                ["--cluster-name"],
                {
                    "help": 'Filter by cluster name, with globs. Ex: "foo*", "*foo"',
                    "action": "store",
                    "default": None,
                    "dest": "cluster_name",
                },
            )
        ],
    )
    @handle_model_exceptions
    def list(self):
        """
        List.
        """
        results = self.model.objects.list(cluster_name=self.app.pargs.cluster_name)
        self.render_list(results)

    @ex(
        help="Change the number of container instances for an ECS Cluster in AWS",
        arguments=[
            (["pk"], {"help": "The primary key for the ECS Service"}),
            (
                ["count"],
                {
                    "help": "Set the number of tasks for the cluster to this",
                    "type": int,
                },
            ),
            (
                ["--force"],
                {
                    "help": "Set the number of tasks for the cluster to this",
                    "action": "store_true",
                    "default": False,
                    "dest": "force",
                },
            ),
        ],
    )
    @handle_model_exceptions
    def scale(self):
        """
        Change desired count for a service.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        self._scale_instances(obj, self.app.pargs.count, self.app.pargs.force)

    # -------------------------
    # -------------------------

    #: Running tasks ordering.
    running_tasks_ordering: str = "Instance"
    #: Running tasks result columns.
    running_tasks_result_columns: dict[str, str] = {
        "Instance": "instanceName",
        "Instance ID": "instanceId",
        "AZ": "availabilityZone",
        "Family": "taskDefinition__family_revision",
        "Launch Type": "launchType",
        "created": "createdAt",
    }

    @ex(
        help="List the running tasks for an ECS Service in AWS.",
        arguments=[
            (["pk"], {"help": "The primary key for the ECS Service"}),
        ],
    )
    @handle_model_exceptions
    def running_tasks(self):
        """
        Running tasks.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        results = obj.running_tasks
        renderer = TableRenderer(
            columns=self.running_tasks_result_columns,
            ordering=self.running_tasks_ordering,
        )
        self.app.print(renderer.render(results))


class ECSClusterSSH(ObjectSSHController):
    """
    Model ecscluster ssh behavior.
    """

    class Meta:
        label = "cluster-ssh"
        description = "SSH to instances for an ECS Cluster"
        help = "SSH to instances for an ECS Cluster"
        stacked_on = "cluster"
        stacked_type = "embedded"

    #: Model.
    model: type[Model] = Cluster

    #: Help overrides.
    help_overrides = {
        "ssh": "SSH to a container instance for an ECS Cluster",
        "run": "Run shell commands on container instances for an ECS Cluster",
    }
