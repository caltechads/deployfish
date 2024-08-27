import os

from cement import App

from . import adapters  # noqa:F401
from .controllers.mysql import MysqlController

__version__ = "1.2.10"


def add_template_dir(app: App):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app: App) -> None:
    app.handler.register(MysqlController)
    app.hook.register('post_setup', add_template_dir)
