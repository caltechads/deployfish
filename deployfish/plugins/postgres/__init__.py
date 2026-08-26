from pathlib import Path

from cement import App

from . import adapters  # noqa:F401

__version__ = "0.1.0"


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
    app.hook.register("post_setup", add_template_dir)
