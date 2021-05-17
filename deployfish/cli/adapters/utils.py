from functools import wraps
import sys

import click

from deployfish.config import get_config
from deployfish.exceptions import RenderException


# ========================
# Decorators
# ========================

def handle_model_exceptions(func):

    @wraps(func)
    def inner(self, *args, **kwargs):
        try:
            obj = func(self, *args, **kwargs)
        except self.model.DoesNotExist as e:
            raise RenderException(click.style(str(e), fg='red'))
        except self.model.MultipleObjectsReturned as e:
            raise RenderException(click.style(str(e), fg='red'))
        except self.model.OperationFailed as e:
            raise RenderException(click.style(str(e), fg='red'))
        except self.DeployfishObjectDoesNotExist as e:
            config = get_config()
            lines = []
            lines.append(click.style('ERROR: could not find a {} identified by "{}" in deployfish.yml\n'.format(
                self.model.__name__,
                e.name
            ), fg='red'))
            lines.append(click.style('Available {}:'.format(e.section), fg='cyan'))
            for item in config.get_section(e.section):
                lines.append('  {}'.format(item['name']))
            lines.append(click.style('\nAvailable environments:', fg='cyan'))
            for item in config.get_section(e.section):
                if 'environment' in item:
                    lines.append('  {}'.format(item['environment']))
            raise RenderException('\n'.join(lines))
        return obj
    return inner


def print_render_exception(func):

    @wraps(func)
    def inner(*args, **kwargs):
        try:
            retval = func(*args, **kwargs)
        except RenderException as e:
            click.echo(e.msg)
            sys.exit(e.exit_code)
        return retval
    return inner
