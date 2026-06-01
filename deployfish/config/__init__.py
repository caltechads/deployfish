from cement import App

from .config import Config

MAIN_APP: App | None = None


class ConfigNotInitializedError(RuntimeError):
    """Raised when config access happens before app initialization."""


def set_app(app: App) -> None:
    """Store active Cement app for config helpers."""
    global MAIN_APP  # noqa: PLW0603
    MAIN_APP = app


def get_config() -> Config:
    """Return initialized deployfish config."""
    if MAIN_APP is None:
        msg = "get_config() called before set_app()"
        raise ConfigNotInitializedError(msg)
    return MAIN_APP.deployfish_config
