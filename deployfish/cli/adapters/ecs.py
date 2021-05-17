import botocore
import click

from .abstract import ClickModelAdapter, ClickBaseModelAdapter, ClickSecretsAdapter
from .commands import (
    ClickRestartServiceCommandMixin,
    ClickScaleInstancesCommandMixin,
    ClickScaleServiceCommandMixin,
    ClickUpdateServiceRelatedTasksCommandMixin,
    ClickListHelperTasksCommandMixin,
    ClickHelperTaskInfoCommandMixin,
    ClickRunHelperTaskCommandMixin,
    ClickTailHelperTaskLogsMixin,
    ClickListHelperTaskLogsMixin,
    ClickRunStandaloneTaskCommandMixin,
    ClickTailStandaloneTaskLogsMixin,
    ClickListStandaloneTaskLogsMixin,
    ClickUpdateHelperTasksCommandMixin,
)
from deployfish.config import get_config
from deployfish.exceptions import RenderException, ConfigProcessingFailed
from deployfish.core.models import Service, Cluster, StandaloneTask, InvokedTask
from deployfish.core.waiters.hooks import ECSDeploymentStatusWaiterHook


class ServiceDereferenceMixin(object):

    def dereference_identifier(self, identifier):
        """
        For Services, allow users to specify just Service.name or Service.environment and dereference that into our
        usual "{cluster_name}:{service_name}" primary key.

        :param identifier str: an identifier for a Service

        :rtype: str
        """
        failure_message = 'Service.name and Service.environment identifiers cannot be used.'
        if ':' not in identifier:
            try:
                config = get_config()
            except ConfigProcessingFailed as e:
                lines = []
                lines.append(click.style('{}'.format(str(e)), fg='yellow'))
                lines.append(click.style(failure_message, fg='yellow'))
                raise RenderException('\n'.join(lines))
            try:
                item = config.get_section_item(self.model.config_section, identifier)
            except KeyError:
                lines = []
                lines.append(click.style(
                    '\nERROR: no service in your deployfish.yml matched "{}".'.format(identifier),
                    fg='red'
                ))
                names = []
                environments = []
                for item in config.get_section(self.model.config_section):
                    names.append(item['name'])
                    if 'environment' in item:
                        environments.append(item['environment'])
                lines.append(click.style('\nAvailable {}s:\n'.format(self.model.__name__), fg='cyan'))
                for name in names:
                    lines.append('  {}'.format(name))
                lines.append(click.style('\nAvailable environments:\n'.format(self.model.__name__), fg='cyan'))
                for environment in environments:
                    lines.append('  {}'.format(environment))
                raise RenderException('\n'.join(lines))
            return '{}:{}'.format(item['cluster'], item['name'])
        return identifier


class ClickServiceAdapter(
    ServiceDereferenceMixin,
    ClickScaleServiceCommandMixin,
    ClickRestartServiceCommandMixin,
    ClickUpdateServiceRelatedTasksCommandMixin,
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
    info_includes = ['secrets', 'deployments']
    info_excludes = ['events']
    list_ordering = 'Service'
    list_result_columns = {
        'Service': 'serviceName',
        'Cluster': 'cluster__name',
        'Version': 'version',
        'D': 'desiredCount',
        'R': 'runningCount',
        'P': 'pendingCount',
        'Created': 'createdAt',
    }
    update_template = 'service--detail:short.tpl'

    def service_waiter(self, obj, **kwargs):
        kwargs['WaiterHooks'] = [ECSDeploymentStatusWaiterHook(obj)]
        kwargs['services'] = [obj.name]
        kwargs['cluster'] = obj.data['cluster']
        self.wait('services_stable', **kwargs)

    create_waiter = service_waiter
    update_waiter = service_waiter

    def delete_waiter(self, obj, **kwargs):
        kwargs['WaiterHooks'] = [ECSDeploymentStatusWaiterHook(obj)]
        kwargs['services'] = [obj.name]
        kwargs['cluster'] = obj.data['cluster']
        try:
            self.wait('services_inactive', **kwargs)
        except botocore.exceptions.WaiterError as e:
            if "DRAINING" not in str(e):
                # If we have tasks in "DRAINING" state, We have unstable containers -- perhaps the service is in
                # trouble.   In this case, we ignore the error because the containers will die soon
                raise


class ClickServiceSecretsAdapter(
    ServiceDereferenceMixin,
    ClickSecretsAdapter
):

    model = Service


class ClickServiceTasksAdapter(
    ServiceDereferenceMixin,
    ClickListHelperTasksCommandMixin,
    ClickHelperTaskInfoCommandMixin,
    ClickRunHelperTaskCommandMixin,
    ClickTailHelperTaskLogsMixin,
    ClickListHelperTaskLogsMixin,
    ClickUpdateHelperTasksCommandMixin,
    ClickBaseModelAdapter
):

    model = Service

    list_helper_tasks_ordering = 'Command Name'
    list_helper_tasks_result_columns = {
        'Command Name': 'command',
        'Revision': 'family_revision',
        'Version': 'version',
        'Launch Type': 'launchType',
        'Schedule': 'schedule_expression'
    }


class ClickStandaloneTaskAdapter(
    ClickRunStandaloneTaskCommandMixin,
    ClickTailStandaloneTaskLogsMixin,
    ClickListStandaloneTaskLogsMixin,
    ClickModelAdapter
):

    model = StandaloneTask

    list_ordering = 'Name'
    list_result_columns = {
        'Name': 'name',
        'Service': {'key': 'serviceName', 'default': ''},
        'Cluster': 'cluster__name',
        'Launch Type': 'launchType',
        'Revision': 'family_revision',
        'Version': 'version',
        'Schedule': 'schedule_expression'
    }


class ClickStandaloneTaskSecretsAdapter(ClickSecretsAdapter):

    model = StandaloneTask


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


class ClickInvokedTaskAdapter(ClickModelAdapter):

    model = InvokedTask

    list_ordering = 'Family'
    list_result_columns = {
        'Family': 'taskDefinition__family_revision',
        'Status': 'lastStatus',
        'pk': 'pk',
    }
