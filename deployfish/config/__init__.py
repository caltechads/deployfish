from typing import Optional

from cement import App

from .config import Config


MAIN_APP: Optional[App] = None

def set_app(app: App) -> None:
    global MAIN_APP  # pylint:disable=global-statement
    MAIN_APP = app

def get_config() -> Config:
    assert MAIN_APP is not None, 'get_config() called before set_app()'
    return MAIN_APP.deployfish_config
