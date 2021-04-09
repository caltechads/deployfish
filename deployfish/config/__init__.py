from .config import Config


config = None


def get_config(**kwargs):
    global config
    if config is None:
        assert kwargs is not {}, 'Config() has not been configured yet.'
        kwargs = {k.lower(): v for k, v in kwargs.items()}
        config = Config.new(**kwargs)
    return config
