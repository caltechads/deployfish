import importlib
import pkg_resources

from jinja2 import FileSystemLoader

import deployfish.core.adapters  # noqa:F401
from deployfish import TEMPLATE_PATHS, jinja_env


def load_local_click_modules():
    for point in pkg_resources.iter_entry_points(group='deployfish.command.plugins'):
        importlib.import_module(point.module_name)


def main():
    global jinja_env
    load_local_click_modules()
    # Update the template paths with whatever any plugins would have added
    jinja_env.loader = FileSystemLoader([str(p) for p in TEMPLATE_PATHS])
    from .cli import cli
    cli(obj={})


if __name__ == '__main__':
    main()
