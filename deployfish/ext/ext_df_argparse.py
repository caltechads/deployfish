from cement.ext.ext_argparse import ArgparseController
from cement.utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class DeployfishArgparseController(ArgparseController):
    """
    We use this subclass of ArgparseController instead of cement's version so that we can
    redefine help strings in subclassess of a base class.
    """

    def _get_command_parser_options(self, command):
        """
        Look on the controller owning a command for a class or instance attribute named
        ``help_overrides``, which is a dict whose keys are method names and whose values
        are help strings, like so::

            class BaseCommands(DeployfishArgparseController):

                class Meta:
                    label = "base-commands"

                @ex(
                    help='The base help string'
                    ...
                )
                def mycommand(self):
                    ...

            class SubclassedCommands(BaseCommands):

                class Meta:
                    label = "subclass-commands"
                    stacked_type = 'nested'
                
                help_overrides = {
                    'info': 'My subclass info help'
                }

        Now the help strings will be::

            > appname base-commands --help
            [...]

            sub-commands:
            {info}
                info      The base help string

            > appname subclass-commands --help
            [...]

            sub-commands:
            {info}
                info      My subclass info help
        """
        kwargs = super()._get_command_parser_options(command)
        if 'help' in kwargs:
            controller = command['controller']
            if hasattr(controller, 'help_overrides'):
                if command['func_name'] in controller.help_overrides:
                    kwargs['help'] = controller.help_overrides[command['func_name']]
        return kwargs
