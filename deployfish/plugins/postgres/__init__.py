from pathlib import Path

from cement import App

from . import adapters  # noqa:F401
from .controllers.postgres import PostgresController
from .hooks import pre_config_interpolate_add_postgres_section

__version__ = "1.0.0"


def add_template_dir(app: App):
    """
    Add template dir.

    Args:
        app: app.

    """
    path = str(Path(__file__).parent / "templates")
    app.add_template_dir(path)


def load(app: App) -> None:
    """
    Load.

    Args:
        app: app.

    """
    app.handler.register(PostgresController)
    app.hook.register("post_setup", add_template_dir)
    app.hook.register(
        "pre_config_interpolate", pre_config_interpolate_add_postgres_section
    )
