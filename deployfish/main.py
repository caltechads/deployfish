import importlib
import pkg_resources

from .cli import cli


def load_local_click_modules():
    for point in pkg_resources.iter_entry_points(group='deployfish.command.plugins'):
        importlib.import_module(point.module_name)


def main():
    load_local_click_modules()
    cli(obj={})


if __name__ == '__main__':
    main()
