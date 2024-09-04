from typing import Type, TYPE_CHECKING

from cement import App

if TYPE_CHECKING:
    from deployfish.config import Config


def pre_config_interpolate_add_mysql_section(app: App, obj: "Type[Config]") -> None:
    """
    Add our "mysql" section to the list of sections on which keyword interpolation
    will be run

    Args:
        app: out cement app
        obj: the :py:class:`deployfish.config.Config` class
    """
    obj.add_processable_section('mysql')
