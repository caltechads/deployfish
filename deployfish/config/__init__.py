from typing import Optional

from .config import Config


config: Optional[Config] = None

def set_config(c: Config) -> None:
    global config  # pylint:disable=global-statement
    config = c

def get_config(**kwargs) -> Config:
    assert config is not None,  'Config() has not been configured yet.'
    return config
