from typing import Any

from cement import ex

from deployfish.core.models import InvokedTask, Model

from .crud import ReadOnlyCrudBase
from .utils import handle_model_exceptions


class ECSInvokedTask(ReadOnlyCrudBase):
    """
    Model ecsinvoked task behavior.
    """

    class Meta:
        label = "invoked-tasks"
        description = "Work with Load Balancer objects"
        help = "Work with Load Balancer objects"
        stacked_type = "nested"
        usage = "Invoked tasks are tasks that either are currently running in ECS, or have run and are now stopped."  # noqa: E501

    #: Model.
    model: type[Model] = InvokedTask

    #: Help overrides.
    help_overrides: dict[str, str] = {
        "info": "Show details about an InvokedTask in AWS",
    }

    #: Info template.
    info_template: str = "detail--invokedtask.jinja2"

    #: List ordering.
    list_ordering: str = "Family"
    #: List result columns.
    list_result_columns: dict[str, Any] = {
        "Family": "taskDefinition__family_revision",
        "Status": "lastStatus",
        "pk": "pk",
    }

    @ex(
        help="List Invoked Tasks in AWS",
        arguments=[
            (["cluster"], {"help": "Name of the cluster to look in for tasks"}),
            (
                ["--service-name"],
                {
                    "help": "Filter by service name",
                    "action": "store",
                    "default": None,
                    "dest": "service",
                },
            ),
            (
                ["--family"],
                {
                    "help": 'Filter by task family"',
                    "action": "store",
                    "default": None,
                    "dest": "family",
                },
            ),
            (
                ["--status"],
                {
                    "help": "Filter by task status.",
                    "action": "store",
                    "default": "RUNNING",
                    "choices": ["RUNNING", "PENDING", "STOPPEd"],
                    "dest": "status",
                },
            ),
            (
                ["--launch-type"],
                {
                    "help": "Filter by launch-type.",
                    "action": "store",
                    "default": "any",
                    "choices": ["any", "EC2", "FARGATE"],
                    "dest": "launch_type",
                },
            ),
        ],
    )
    @handle_model_exceptions
    def list(self):
        """
        List.
        """
        results = self.model.objects.list(
            self.app.pargs.cluster,
            service=self.app.pargs.service,
            family=self.app.pargs.family,
            launch_type=self.app.pargs.launch_type,
            status=self.app.pargs.status,
        )
        self.render_list(results)
