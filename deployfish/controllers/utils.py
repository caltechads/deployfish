from functools import wraps
from typing import Callable

import click
from deployfish.core.ssh import SSHMixin

from deployfish.exceptions import (
    ConfigProcessingFailed,
    MultipleObjectsReturned,
    NoSuchConfigSection,
    NoSuchConfigSectionItem,
    ObjectDoesNotExist,
    SchemaException
)


# ========================
# Decorators
# ========================

def handle_model_exceptions(func: Callable) -> Callable:  # noqa:C901
    """
    We use this decorator to wrap cement command methods on Controller classes.

    We're catching all the kinds of execptions we expect to see in normal operation while letting others
    display their stack traces normally.
    """

    @wraps(func)
    def inner(self, *args, **kwargs):
        try:
            obj = func(self, *args, **kwargs)
        except (
            ObjectDoesNotExist,
            MultipleObjectsReturned,
            self.model.OperationFailed,
            self.model.ReadOnly,
            self.loader.DeployfishSectionDoesNotExist,
            SchemaException,
            ConfigProcessingFailed,
            NoSuchConfigSection,
            SSHMixin.NoSSHTargetAvailable
        ) as e:
            self.app.print(click.style(str(e), fg='red'))
        except NoSuchConfigSectionItem as e:
            lines = []
            lines.append(click.style('ERROR: {}'.format(str(e)), fg='red'))
            lines.append(
                click.style('Available {}s in the "{}:" section of deployfish.yml:'.format(
                    self.model.__name__,
                    e.section
                ), fg='cyan')
            )
            for item in self.app.deployfish_config.get_section(e.section):
                lines.append('  {}'.format(item['name']))
            environments = []
            for item in self.app.deployfish_config.get_section(e.section):
                if 'environment' in item:
                    environments.append('  {}'.format(item['environment']))
            if environments:
                lines.append(click.style('\nAvailable environments:', fg='cyan'))
                lines.extend(environments)
            lines.append('')
            self.app.print('\n'.join(lines))
        else:
            return obj
    return inner
