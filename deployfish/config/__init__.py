from cement import App

from .config import Config

#: Active Cement app used by config helper accessors.
MAIN_APP: App | None = None


class ConfigNotInitializedError(RuntimeError):
    """Raised when config access happens before app initialization."""


def set_app(app: App) -> None:
    """
    Store active Cement app for config helpers.

    Args:
        app: Cement app whose config helpers should be used.

    """
    global MAIN_APP  # noqa: PLW0603
    MAIN_APP = app


def get_config() -> Config:
    """
    Return initialized deployfish config.

    Raises:
        ConfigNotInitializedError: App has not been registered yet.

    Returns:
        Config object attached to active Cement app.

    """
    if MAIN_APP is None:
        msg = "get_config() called before set_app()"
        raise ConfigNotInitializedError(msg)
    return MAIN_APP.deployfish_config
