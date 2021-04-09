from .abstract import ClickModelAdapter, ClickSecretsAdapter
from .commands import (
    ClickRestartServiceCommandMixin,
    ClickScaleInstancesCommandMixin,
    ClickScaleServiceCommandMixin,
)
from deployfish.core.models import Service, Cluster
from deployfish.core.waiters.hooks import ECSDeploymentStatusWaiterHook


class ClickServiceAdapter(
    ClickScaleServiceCommandMixin,
    ClickRestartServiceCommandMixin,
    ClickModelAdapter
):

    model = Service

    # Loading secrets from parameter store takes FOREVER, so pass these Service factory
    # kwargs to disable secrets loading for those operations that don't need them
    factory_kwargs = {
        'delete': {'load_secrets': False},
        'ssh': {'load_secrets': False},
        'exec': {'load_secrets': False},
        'tunnel': {'load_secrets': False},
    }
    list_ordering = 'Service'
    list_result_columns = {
        'Service': 'serviceName',
        'Cluster': 'cluster__name',
        'Version': 'version',
        'Desired count': 'desiredCount',
        'Running count': 'runningCount'
    }
    update_template = 'service--detail:short.tpl'

    def service_waiter(self, obj, **kwargs):
        kwargs['WaiterHooks'] = [ECSDeploymentStatusWaiterHook(obj)]
        kwargs['services'] = [obj.name]
        kwargs['cluster'] = obj.data['cluster']
        self.wait('services_stable', **kwargs)

    create_waiter = service_waiter
    update_waiter = service_waiter
    delete_waiter = service_waiter


class ClickServiceSecretsAdapter(ClickSecretsAdapter):

    model = Service


class ClickClusterAdapter(ClickScaleInstancesCommandMixin, ClickModelAdapter):

    model = Cluster

    list_result_columns = {
        'Name': 'clusterName',
        'Status': 'status',
        'Instances': 'registeredContainerInstancesCount',
        'Services': 'activeServicesCount',
        'Running Tasks': 'runningTasksCount',
        'Pending Tasks': 'pendingTasksCount'
    }
