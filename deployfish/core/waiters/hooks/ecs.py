from datetime import datetime
from textwrap import wrap

import click
from tabulate import tabulate
from tzlocal import get_localzone

from deployfish.core.models import Service

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

    def __call__(self, status, response, num_attempts, **kwargs):
        cluster = kwargs['cluster']
        service = kwargs['services'][0]
        if status == 'waiting':
            service = Service.objects.get('{}:{}'.format(cluster, service))
            click.secho('\n\nDeployment status:', fg='cyan')
            click.secho('------------------\n', fg='cyan')
            self.display_deployments(service.deployments)
            click.secho('\n\nService events:', fg='cyan')
            click.secho('---------------\n', fg='cyan')
            self.display_events(service.events)
            self.timestamp = self.our_timezone.localize(datetime.now())
            click.secho('\n')
            click.secho('=' * 72, fg='white', bg='yellow')
        elif status == 'success':
            click.secho('\n\nService is stable!', fg='green')
        elif status == 'failure' or status == 'error':
            click.secho('\n\nService failed to stabilize!', fg='red')
        elif status == 'timeout':
            click.secho('\n\nTimed out waiting for the service to stablize!\n\n', fg='red')
            click.secho(
                'NOTE: this does not necessarily mean your deployment failed: check the AWS console to be sure.'
            )
