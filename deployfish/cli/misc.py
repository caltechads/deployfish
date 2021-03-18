from __future__ import print_function

import os
import subprocess
import sys

import click

try:
    from textwrap import indent
except ImportError:
    # We're in Python 2
    def indent(text, prefix, predicate=None):
        """Adds 'prefix' to the beginning of selected lines in 'text'.

        If 'predicate' is provided, 'prefix' will only be added to the lines
        where 'predicate(line)' is True. If 'predicate' is not provided,
        it will default to adding 'prefix' to all non-empty lines that do not
        consist solely of whitespace characters.
        """
        if predicate is None:
            def predicate(line):
                return line.strip()

        def prefixed_lines():
            for line in text.splitlines(True):
                yield (prefix + line if predicate(line) else line)
        return ''.join(prefixed_lines())


from deployfish.aws.ecs import Service, Task
from deployfish.aws.systems_manager import ParameterStore
from deployfish.config import Config


class FriendlyServiceFactory:
    """
    This is a wrapper for ``Service`` that prints a friendly message when we're given a service or environment name that
    doesn't exist.
    """

    @staticmethod
    def new(service_name, config=None):
        try:
            return Service(service_name, config=config)
        except KeyError:
            click.secho('No service or environment named "{}"\n'.format(service_name), fg='red')
            config.info()
            sys.exit(1)


class AbstractClickAdapter(object):

    colors = {
        "title": "bright_cyan",
        "section": "yellow",
        "item": "white",
        "normal": "white",
        "success": "green",
        "warning": "yellow",
        "critical": "red"
    }

    def title(self, text, value=None):
        return self.section(text, value=value, color="title")

    def section(self, text, value=None, color="section"):
        if value:
            text = "{}:  {}".format(text, value)
        return click.style(text, fg=self.colors[color])

    def style(self, text, color="normal"):
        return click.style(text, fg=self.colors[color])

    def key_value(self, key, value, color="item", indent=2, width=20):
        pformat = '{:<%d}: {}' % width
        rendered = self.style(pformat.format(key, value), color)
        if indent:
            rendered = self.indent(rendered, spaces=indent)
        return rendered

    def key_list(self, key, values, color="item", indent=2, width=20):
        return self.key_value(key, ','.join(values), color=color, indent=indent, width=width)

    def indent(self, text, spaces=4):
        if isinstance(text, list):
            lines = []
            for line in text:
                lines.append(indent(line, " " * spaces))
            return lines
        else:
            return indent(text, "  " * spaces)

    def render(self, join=True):
        raise NotImplementedError


class ClickTaskDefinitionAdapter(AbstractClickAdapter):

    def __init__(self, task_definition):
        self.task_definition = task_definition

    def _render_containers(self, indent=0):
        lines = []
        lines.append(self.section('containers:'))
        for container in self.task_definition.containers:
            section = []
            section.append(self.section(container.name))
            section.append(self.key_value('image', container.image))
            section.append(self.key_value('cpu', container.cpu))
            if container.memory:
                section.append(self.key_value('memory', container.memory))
            if container.memoryReservation:
                section.append(self.key_value('memory_reservation', container.memoryReservation))
            if container.portMappings:
                for port in container.portMappings:
                    section.append(self.key_value('port', port))
            if container.extraHosts:
                for host in container.extraHosts:
                    section.append(self.key_value('extra_host', host))
            lines.extend(self.indent(section))
        return lines

    def _render_volume(self, volume):
        lines = []
        lines.append(self.section('{}: {}'.format(volume['name'], volume.get('path', 'NO-PATH'))))
        if 'config' in volume:
            lines.append(self.key_value('scope', volume['config'].get('scope', 'task')))
            lines.append(self.key_value('autoprovision', volume['config'].get('autoprovision', 'True')))
            lines.append(self.key_value('driver', volume['config']['driver']))
            if 'driverOpts' in volume['config']:
                lines.append(self.style('driverOpts:', 'item'))
                for key, value in volume['config']['driverOpts'].items():
                    lines.append(self.key_value(key, value, indent=4))
            if 'labels' in volume['config']:
                lines.append(self.style('labels:', 'item'))
                for key, value in volume['config']['labels'].items():
                    lines.append(self.key_value(key, value, indent=4))
        return lines

    def render(self, join=False):
        lines = []
        if self.task_definition.family_revision:
            lines.append(self.title(self.task_definition.family_revision))
        else:
            lines.append(self.title('{}:TBD'.format(self.task_definition.family)))
        lines.append(self.key_value('family', self.task_definition.family))
        lines.append(self.key_value('network_mode', self.task_definition.networkMode))
        if self.task_definition.taskRoleArn:
            lines.append(self.key_value('task_role_arn', self.task_definition.taskRoleArn))
        if self.task_definition.executionRoleArn:
            lines.append(self.key_value('execution_role', self.task_definition.executionRoleArn))
        if self.task_definition.cpu:
            lines.append(self.key_value('cpu', self.task_definition.cpu))
        if self.task_definition.memory:
            lines.append(self.key_value('memory', self.task_definition.memory))
        if self.task_definition.volumes:
            lines.append(self.section('volumes:'))
            for volume in self.task_definition.volumes:
                lines.extend(self.indent(self._render_volume(volume)))
        lines.extend(self.indent(self._render_containers()))
        if join:
            return '\n'.join(lines)
        else:
            return lines


class ClickServiceAdapter(AbstractClickAdapter):

    class ASGScaleException(Exception):

        def __init__(self, msg):
            self.msg = msg

    class TimeoutException(Exception):

        def __init__(self, msg):
            self.msg = msg

    def __init__(self, service):
        self.service = service
        self.parameters = ClickParameterAdapter(service)
        self.desired_task_definition = ClickTaskDefinitionAdapter(service.desired_task_definition)
        self.active_task_definition = ClickTaskDefinitionAdapter(service.active_task_definition)
        self.desired_helper_tasks = {
            name: ClickTaskDefinitionAdapter(task.desired_task_definition) for name, task in service.tasks.items()
        }
        self.active_helper_tasks = {
            name: ClickTaskDefinitionAdapter(task.active_task_definition) for name, task in service.tasks.items()
        }

    def _render_autoscaling_group(self):
        lines = []
        if self.service.asg.exists():
            lines.append(self.section('autoscaling group:'))
            lines.append(self.key_value('name', self.service.asg.name))
            lines.append(self.key_value('count', self.service.asg.count))
            lines.append(self.key_value('min_size', self.service.asg.min))
            lines.append(self.key_value('max_size', self.service.asg.max))
        return lines

    def _render_elb(self, load_balancer):
        lines = []
        lines.append(self.key_value('load_balancer_id', load_balancer['load_balancer_name']))
        lines.append(self.key_value('container_name', load_balancer['container_name'], indent=4))
        lines.append(self.key_value('container_port', load_balancer['container_port'], indent=4))
        return lines

    def _render_target_group(self, target_group):
        lines = []
        lines.append(self.key_value('target_group_arn', value=target_group['target_group_arn']))
        lines.append(self.key_value('container_name', target_group['container_name'], indent=4))
        lines.append(self.key_value('container_port', target_group['container_port'], indent=4))
        return lines

    def _render_load_balancer(self):
        lines = []
        if self.service.load_balancer:
            lines.append(self.section('load_balancer:'))
            lines.append(self.key_value('service_role_arn', self.service.roleArn))
            lb = self.service.load_balancer
            if isinstance(lb, dict):
                if self.service.load_balancer['type'] == 'elb':
                    lines.extend(self._render_elb(lb))
                else:
                    lines.extend(self._render_target_group(lb))
            else:
                for target_group in lb:
                    lines.extend(self._render_target_group(target_group))
        return lines

    def _render_scaling_config(self):
        lines = []
        if self.service.scaling:
            lines.append(self.section('application_scaling:'))
            lines.append(self.key_value('min_capacity', self.service.scaling.MinCapacity))
            lines.append(self.key_value('max_capacity', self.service.scaling.MaxCapacity))
            lines.append(self.key_value('role_arn', self.service.scaling.RoleARN))
            lines.append(self.key_value('resource_id', self.service.scaling.resource_id))
        return lines

    def render_helper_tasks(self, state='live', join=True):
        assert state in ['live', 'desired']
        lines = []
        if self.service.tasks:
            lines.append(self.title('Helper Tasks [{}]:'.format(state)))
            if state == "live":
                helper_tasks = self.active_helper_tasks
            else:
                helper_tasks = self.desired_helper_tasks
            for name, task in helper_tasks.items():
                lines.append(self.indent(self.section(name), spaces=2))
                lines.extend(self.indent(task.render(), spaces=4))
        if join:
            return "\n".join(lines)
        else:
            return lines

    def render(self, state='live', join=True):
        assert state in ['live', 'desired']
        lines = []
        lines.append(self.title('Service [{}]:'.format(state)))
        lines.append(self.key_value('service_name', self.service.serviceName))
        lines.append(self.key_value('cluster_name', self.service.clusterName))
        lines.append(self.key_value('count', self.service.count))
        lines.append(self.key_value('launch_type', self.service.launchType))
        lines.append(self.key_value('minHealthyPercent', self.service.minimumHealthyPercent))
        lines.append(self.key_value('maximumPercent', self.service.maximumPercent))
        lines.append(self.key_value('scheduling_strategy', self.service.schedulingStrategy))
        lines.extend(self.indent(self._render_autoscaling_group()))
        lines.extend(self.indent(self._render_load_balancer()))
        lines.extend(self.indent(self._render_scaling_config()))
        lines.append('')
        lines.append(self.title('Service Task Definition [{}]:'.format(state)))
        if state == 'live':
            lines.extend(self.indent(self.active_task_definition.render(), spaces=2))
        else:
            lines.extend(self.indent(self.desired_task_definition.render(), spaces=2))
        lines.append('')
        lines.extend(self.render_helper_tasks(state=state))
        if join:
            return "\n".join(lines)
        else:
            return lines

    def wait(self, timeout):
        click.secho("\n  Waiting until the service is stable with our new task def ...", fg='white')
        if self.service.wait_until_stable(timeout):
            click.secho("  Done.", fg='white')
        else:
            raise self.TimeoutException(self.style("  FAILURE: the service failed to stabalize.", 'critical'))

    def scale_asg(self, count=None, force=False):
        if not count:
            count = self.service.count
        if self.service.asg.exists():
            if count < self.service.asg.min:
                if not force:
                    lines = []
                    lines.append(
                        self.style('Service count {} is less than min_size of {} on AutoscalingGroup "{}".'.format(
                            count,
                            self.service.asg.min,
                            self.service.asg.name
                        )), 'critical'
                    )
                    lines.append('\nEither:')
                    lines.append('  (1) use --force-asg to also reduce AutoscalingGroup min_size to {}'.format(count))
                    lines.append('  (2) specify service count >= {}'.format(self.service.asg.min))
                    lines.append('  (3) use --no-asg to not change the AutoscalingGroup size')
                    raise self.ASGScaleException('\n'.join(lines))
                else:
                    click.secho(self.style(
                        'Updating MinCount on AutoscalingGroup "{}" to {}.'.format(self.service.serviceName, count)
                    ))
            if count > self.service.asg.max:
                if not force:
                    lines = []
                    lines.append(
                        self.style('Service count {} is greater than max_size of {} on AutoscalingGroup "{}".'.format(
                            count,
                            self.service.asg.max,
                            self.service.asg.name
                        ), 'critical')
                    )
                    lines.append('\nEither:')
                    lines.append('  (1) use --force-asg to also increase AutoscalingGroup max_size to {}'.format(count))
                    lines.append('  (2) specify service count <= {}'.format(self.service.asg.max))
                    raise self.ASGScaleException('\n'.join(lines))
                else:
                    click.secho(self.style(
                        'Updating MaxCount on AutoscalingGroup "{}" to {}.'.format(self.service.serviceName, count)
                    ))
            click.secho('Updating DesiredCount on AutoscalingGroup "{}" to {}.'.format(
                self.service.serviceName,
                count
            ), fg="white")
            self.service.asg.scale(count, force=force)


class ClickTaskAdapter(AbstractClickAdapter):

    def __init__(self, task):
        self.task = task
        self.parameters = ClickParameterAdapter(task)
        self.desired_task_definition = ClickTaskDefinitionAdapter(task.desired_task_definition)
        if task.active_task_definition:
            self.active_task_definition = ClickTaskDefinitionAdapter(task.active_task_definition)
        else:
            self.active_task_definition = None

    def _render_vpc_configuration(self):
        lines = []
        if self.task.vpc_configuration:
            lines.append(self.section('vpc_configuration:'))
            lines.append(self.key_list('subnets', self.task.vpc_configuration['subnets']))
            lines.append(self.key_list('security_groups', self.task.vpc_configuration['securityGroups']))
        return lines

    def render(self, state='live', join=True):
        assert state in ['live', 'desired']
        lines = []
        lines.append(self.title('Task [desired]:'.format(state)))
        lines.append(self.key_value('task_name', self.task.taskName))
        if self.task.cluster_specified:
            lines.append(self.key_value('cluster_name', self.task.clusterName))
        else:
            lines.append(self.key_value('cluster_name', 'UNSPECIFIED'))
        if self.task.group:
            lines.append(self.key_value('group', self.task.grup))
        lines.append(self.key_value('count', self.task.desired_count))
        lines.append(self.key_value('launch_type', self.task.launchType))
        lines.append(self.key_value('platform_version', self.task.platform_version))
        if self.task.schedule_expression:
            lines.append(self.key_value('schedule_expression', self.task.schedule_expression))
        lines.extend(self.indent(self._render_vpc_configuration()))
        lines.append('')
        lines.append(self.title('Task Definition [{}]:'.format(state)))
        if state == 'live':
            if self.active_task_definition:
                lines.extend(self.indent(self.active_task_definition.render(), spaces=2))
            else:
                lines.append(self.style('\nNo version of this task exists in AWS.', 'critical'))
        else:
            lines.extend(self.indent(self.desired_task_definition.render(), spaces=2))
        if join:
            return "\n".join(lines)
        else:
            return lines


class ClickParameterAdapter(AbstractClickAdapter):

    def __init__(self, obj):
        self.obj = obj
        self.name = self.get_obj_name(obj)

    def get_obj_name(self, obj):
        """
        Return the human name for this Task or Service.

        Raises ValueError if ``obj`` is not a Task or Service.

        :param obj Union[Task, Service]: the object whose name we want

        :rtype: str
        """
        if isinstance(obj, Service):
            return 'Service(name="{}")'.format(obj.serviceName)
        elif isinstance(obj, Task):
            return 'Task(name="{}")'.format(obj.taskName)
        else:
            raise ValueError('Unknown object type: {}'.format(repr(obj)))

    def _sort_parameters(self, parameters):
        creates = []
        updates = []
        deletes = []
        no_changes = []
        not_exists = []
        for parameter in parameters:
            if parameter.should_exist:
                if not parameter.exists:
                    if not parameter.is_external:
                        creates.append(parameter)
                    else:
                        not_exists.append(parameter)
                elif parameter.needs_update:
                    updates.append(parameter)
                else:
                    no_changes.append(parameter)
            else:
                deletes.append(parameter)
        return creates, updates, deletes, no_changes, not_exists

    def _render_parameters(self, parameters, label, color='normal'):
        lines = []
        if parameters:
            lines.append(self.style('{}:'.format(label), "section"))
            for p in parameters:
                lines.append(self.indent(self.style(str(p), color), spaces=2))
            lines.append('')
        return lines

    def diff(self, parameters=None, join=True):
        if not parameters:
            parameters = self.obj.get_config()
        if parameters:
            creates, updates, deletes, no_changes, not_exists = self._sort_parameters(parameters)
            lines = []
            lines.append('Diff between local and AWS parameters for {}":'.format(self.name))
            lines.append('')
            lines.extend(self._render_parameters(no_changes, 'Already correct in AWS'))
            lines.extend(self._render_parameters(creates, 'Needs creating', color='success'))
            lines.extend(self._render_parameters(updates, 'Needs updating', color='warning'))
            lines.extend(self._render_parameters(deletes, 'Needs deleting', color='warning'))
            lines.extend(
                self._render_parameters(not_exists, 'External parameters that do not exist in AWS', color='critical')
            )
        else:
            lines.append(self.style('No config parameters defined for {}.'.format(self.name), 'success'))
        if join:
            return "\n".join(lines)
        else:
            return lines

    def list(self, parameters=None, join=True):
        if not parameters:
            parameters = self.obj.get_config()
        if parameters:
            lines = []
            lines.append(self.style('Live values of parameters for {}'.format(self.name), "section"))
        for p in parameters:
            if p.exists:
                if p.should_exist:
                    lines.append(self.style("  {}".format(p.display(p.key, p.aws_value)), "success"))
            else:
                lines.append(self.style("  {}".format(p.display(p.key, "[NOT IN AWS]")), "critical"))
        if join:
            return "\n".join(lines)
        else:
            return lines

    def write(self, dry_run=False, join=True):
        """
        Update our AWS Parameter Store parameters from the config: values in ``obj``, a configured
        `Task` or `Section` object.
        """
        parameters = self.obj.get_config()
        if not parameters:
            return [self.style('No config parameters defined for {}.'.format(self.name), 'success')]
        lines = []
        lines.extend(self.diff(parameters))
        if not dry_run:
            self.obj.write_config()
            lines.append('')
            lines.append(self.style('Updated parameters for {} in AWS.'.format(self.name), 'success'))
        else:
            lines.append('')
            lines.append(self.style('DRY RUN: not making changes in AWS', "warning"))
        if join:
            return "\n".join(lines)
        else:
            return lines

    def to_env_file(self):
        parameters = self.obj.get_config()
        lines = []
        for p in parameters:
            if p.exists and p.should_exist:
                lines.append("{}={}".format(p.key, p.aws_value))
        return "\n".join(lines)


# -----------------------------------------------------------------
# Entrypoints
# -----------------------------------------------------------------

class AbstractClickEntrypoint(AbstractClickAdapter):
    """
    The main method for this class is self.entrypoint(), which exports the AWS Parameter Store parameters
    for our Service or Task into the container environment.

    To use this, subclass this class and set the following class attributes:

        * object_type:  Set to "task" or "service"
        * deployfish_yml_section:  Set to "tasks" or "services"
        * name_env_var: What environment variable contains the name of our service/task?
        * parameter_prefix: if our parameters in Parameter Store have a prefix (as tasks do), set this to that prefix
    """

    object_type = None
    deployfish_yml_section = None
    name_env_var = None
    parameter_prefix = ''

    class NoSuchEntryException(Exception):
        pass

    def __init__(self, config_file=None):
        if not config_file:
            config_file = 'deployfish.yml'
        kwargs = {
            'interpolate': False,
            'use_aws_section': False
        }
        if config_file:
            kwargs['filename'] = config_file
        self.config = Config(**kwargs)
        self.yml = None

    @property
    def name(self):
        return os.environ.get(self.name_env_var, None)

    @property
    def cluster_name(self):
        return os.environ.get('DEPLOYFISH_CLUSTER_NAME', None)

    def get_object_config(self):
        """
        Return the raw deployfish configuration for our object.

        If no such config is found in our deployfish.yml, raise self.DoesNotExist.

        :rtype: dict
        """
        try:
            self.yml = self.config.get_section_item(self.deployfish_yml_section, self.name)
        except KeyError:
            msg = "Our container's deployfish config file '{}' does not have a {} named '{}'".format(
                self.config.filename,
                self.object_type,
                self.name
            )
            raise self.DoesNotExist(msg)

    def get_parameters(self):
        """
        If our deployfish.yml config data has a `config:` section, return a `ParameterStore` object
        populated with the current values of thoe parameters from ParamterStore.  Otherwise, return
        an empty list.

        :rtype: Union(list, ParameterStore)
        """
        exists = []
        should_not_exist = []
        not_exists = []
        if 'config' in self.yml:
            parameter_name = self.parameter_prefix + self.name
            params = ParameterStore(parameter_name, self.name, yml=self.yml['config'])
            params.populate()
        for param in params:
            if param.exists:
                if param.should_exist:
                    exists.append(param)
                else:
                    should_not_exist.append(param)
            else:
                not_exists.append(param)
        return exists, should_not_exist, not_exists

    def set_environment(self):
        """
        Set an environment variable for each AWS Parameter Store parameter we have for our object.

        :rtype: list(str)
        """
        exists, should_not_exist, not_exists = self.get_parameters()
        for param in exists:
            os.environ[param.key] = param.aws_value
        for param in should_not_exist:
            click.echo(
                "event='deploy.entrypoint.parameter.ignored.not_in_deployfish_yml' "
                "{}='{}' parameter='{}'".format(self.object_type, self.name, param.name)
            )
        for param in not_exists:
            click.echo("event='deploy.entrypoint.parameter.ignored.not_in_aws' {}='{}' parameter='{}'".format(
                self.object_type, self.name, param.name
            ))

    def diff(self, params):
        """
        Print what would be set in the environment, but don't set environment variables.


        :rtype: list(str)
        """
        exists, should_not_exist, not_exists = self.get_parameters()
        click.secho(self.style("Would have set these environment variables:", "success"))
        for param in exists:
            click.echo('  {}={}'.format(param.key, param.aws_value))
        click.secho(self.style("\nIn AWS but not in the {} config: section".format(self.object_type), "warning"))
        for param in should_not_exist:
            click.echo('  {}={}'.format(param.key, param.aws_value))
        click.secho(self.style("\nIn the {} config: section but not in AWS:", "critical"))
        for param in not_exists:
            click.echo('  {}'.format(param.key))

    def entrypoint(self, command, dry_run=False):
        if self.name and self.cluster_name:
            self.get_object_config()
            if dry_run:
                self.diff()
                click.secho('\n\nCOMMAND: {}'.format(command))
            else:
                self.set_environment()
                subprocess.call(command)


class ClickServiceEntrypoint(AbstractClickEntrypoint):

    object_type = 'service'
    section = 'services'
    name_env_var = 'DEPLOYFISH_SERVICE_NAME'


class ClickTaskEntrypoint(AbstractClickEntrypoint):

    object_type = 'task'
    section = 'tasks'
    name_env_var = 'DEPLOYFISH_TASK_NAME'
    paramter_prefix = 'task-'
