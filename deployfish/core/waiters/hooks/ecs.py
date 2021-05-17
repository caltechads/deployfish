from datetime import datetime
from textwrap import wrap

import click
from tabulate import tabulate
from tzlocal import get_localzone

from deployfish.core.models import Service, InvokedTask

from .abstract import AbstractWaiterHook


class ECSDeploymentStatusWaiterHook(AbstractWaiterHook):
    """
    This for both the 'services_stable' and 'services_inactive' waiters on ECS.
    """

    def __init__(self, obj):
        super(ECSDeploymentStatusWaiterHook, self).__init__(obj)
        self.our_timezone = get_localzone()
        self.start = self.our_timezone.localize(datetime.now())
        self.timestamp = self.start

    def display_deployments(self, deployments):
        rows = []
        for d in deployments:
            if d['status'] == 'PRIMARY':
                fg = 'green'
            elif d['status'] == 'ACTIVE':
                fg = 'yellow'
            else:
                fg = 'white'
            rows.append([
                click.style(d['status'], fg=fg),
                click.style(d['taskDefinition'], fg=fg),
                click.style(str(d['desiredCount']), fg=fg),
                click.style(str(d['pendingCount']), fg=fg),
                click.style(str(d['runningCount']), fg=fg)
            ])
        click.secho(tabulate(rows, headers=['Status', 'Task def', 'Desired', 'Pending', 'Running']))

    def display_events(self, events):
        rows = []
        events = sorted(events, key=lambda x: x['createdAt'])
        events.reverse()
        for i, e in enumerate(events):
            if e['createdAt'] < self.timestamp:
                fg = 'white'
            else:
                fg = 'yellow'
            if e['createdAt'] < self.start:
                break
            # FIXME: make the time display be "N sec ago"
            timestamp = e['createdAt']
            rows.append([
                click.style(timestamp.strftime('%Y-%m-%d %H:%M:%S'), fg=fg),
                click.style('\n'.join(wrap(e['message'], 80)), fg=fg)
            ])
        click.secho(tabulate(rows, headers=['Timestamp', 'Message']))

    def waiting(self, status, response, num_attempts, **kwargs):
        cluster = kwargs['cluster']
        service = kwargs['services'][0]
        service = Service.objects.get('{}:{}'.format(cluster, service))
        click.secho('\n\nDeployment status:', fg='cyan')
        click.secho('------------------\n', fg='cyan')
        self.display_deployments(service.deployments)
        click.secho('\n\nService events:', fg='cyan')
        click.secho('---------------\n', fg='cyan')
        self.display_events(service.events)
        self.timestamp = self.our_timezone.localize(datetime.now())
        click.secho('\n')
        self.mark(status, response, num_attempts, **kwargs)

    def success(self, status, response, num_attempts, **kwargs):
        click.secho('\n\nService is stable!', fg='green')

    def failure(self, status, response, num_attempts, **kwargs):
        click.secho('\n\nService failed to stabilize!', fg='red')
    error = failure

    def timeout(self, status, response, num_attempts, **kwargs):
        click.secho('\n\nTimed out waiting for the service to stablize!\n\n', fg='red')
        click.secho(
            'NOTE: this does not necessarily mean your deployment failed: check the AWS console to be sure.'
        )


class ECSTaskStatusHook(AbstractWaiterHook):
    """
    This for the 'tasks_stopped'' waiters on ECS, and prints the status of our tasks on each iteration.
    """

    def __init__(self, obj):
        super(ECSTaskStatusHook, self).__init__(obj)
        self.our_timezone = get_localzone()
        self.start = self.our_timezone.localize(datetime.now())
        self.timestamp = self.start

    def waiting(self, status, response, num_attempts, **kwargs):
        tasks = [InvokedTask.objects.get('{}:{}'.format(kwargs['cluster'], arn)) for arn in kwargs['tasks']]
        table = []
        print()
        for i, task in enumerate(tasks):
            row = [
                i,
                kwargs['cluster'],
                task.arn.rsplit('/', 1)[1],
                task.data['lastStatus'],
                task.data['createdAt'].strftime('%Y-%m-%d %H:%M:%S'),
            ]
            if 'startedAt' in task.data:
                row.append(task.data['startedAt'].strftime('%Y-%m-%d %H:%M:%S'))
            else:
                row.append('Not Started')
            table.append(row)
        click.secho(tabulate(table, headers=['#', 'Cluster', 'ID', 'Status', 'Created', 'Started']))
        self.mark(status, response, num_attempts, **kwargs)

    def success(self, status, response, num_attempts, **kwargs):
        tasks = [InvokedTask.objects.get('{}:{}'.format(kwargs['cluster'], arn)) for arn in kwargs['tasks']]
        click.secho('\n\nFinal Task status:', fg='cyan')
        click.secho('-----------------\n', fg='cyan')
        table = []
        for i, task in enumerate(tasks):
            row = [
                i,
                kwargs['cluster'],
                task.arn.rsplit('/', 1)[1],
                task.data['lastStatus'],
                task.data['stopCode'],
                task.data['stoppedAt'].strftime('%Y-%m-%d %H:%M:%S')
            ]
            table.append(row)
        click.secho(tabulate(table, headers=['#', 'Cluster', 'ID', 'Status', 'Stop Code', 'Stopped']))
        print()
    failure = success
    error = success

    def timeout(self, status, response, num_attempts, **kwargs):
        click.secho('\n\nTimed out waiting for the tasks to finish!\n\n', fg='red')


class ECSTaskLogsHook(AbstractWaiterHook):
    """
    This for the 'tasks_stopped'' waiters on ECS.
    """

    def __init__(self, obj):
        super(ECSTaskStatusHook, self).__init__(obj)
        self.our_timezone = get_localzone()
        self.start = self.our_timezone.localize(datetime.now())
        self.timestamp = self.start

    def waiting(self, status, response, num_attempts, **kwargs):
        tasks = [InvokedTask.objects.get('{}:{}'.format(kwargs['cluster'], arn)) for arn in kwargs['tasks']]
        click.secho('\n\nTask status:', fg='cyan')
        click.secho('------------\n', fg='cyan')
        table = []
        for i, task in enumerate(tasks):
            row = [
                i,
                kwargs['cluster'],
                task.arn.rsplit('/', 1)[1],
                task.data['lastStatus'],
                task.data['createdAt'].strftime('%Y-%m-%d %H:%M:%S'),
            ]
            if 'startedAt' in task.data:
                row.append(task.data['startedAt'].strftime('%Y-%m-%d %H:%M:%S'))
            else:
                row.append('Not Started')
            table.append(row)
        click.secho(tabulate(table, headers=['#', 'Cluster', 'ID', 'Status', 'Created', 'Started']))
        click.secho('\n')
        self.mark(status, response, num_attempts, **kwargs)

    def success(self, status, response, num_attempts, **kwargs):
        tasks = [InvokedTask.objects.get('{}:{}'.format(kwargs['cluster'], arn)) for arn in kwargs['tasks']]
        click.secho('\n\nTask status:', fg='cyan')
        click.secho('------------\n', fg='cyan')
        table = []
        for i, task in enumerate(tasks):
            row = [
                i,
                kwargs['cluster'],
                task.arn.rsplit('/', 1)[1],
                task.data['lastStatus'],
                task.data['stopCode'],
                task.data['stoppedAt'].strftime('%Y-%m-%d %H:%M:%S')
            ]
            table.append(row)
        click.secho(tabulate(table, headers=['#', 'Cluster', 'ID', 'Status', 'Stop Code', 'Stopped']))
    failure = success
    error = success

    def timeout(self, status, response, num_attempts, **kwargs):
        click.secho('\n\nTimed out waiting for the tasks to finish!\n\n', fg='red')
