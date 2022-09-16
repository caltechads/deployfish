import os
from typing import Any, Optional, Dict

from cement import App, init_defaults
from cement.core.exc import CaughtSignal

import deployfish.core.adapters  # noqa:F401,F403  # pylint:disable=unused-import

from .config import Config, set_app
from .controllers import (
    Base,
    BaseService,
    BaseServiceDockerExec,
    BaseServiceSSH,
    BaseServiceSecrets,
    BaseTunnel,
    EC2ClassicLoadBalancer,
    EC2LoadBalancer,
    EC2LoadBalancerListener,
    EC2LoadBalancerTargetGroup,
    ECSCluster,
    ECSClusterSSH,
    ECSInvokedTask,
    ECSService,
    ECSServiceCommands,
    ECSServiceCommandLogs,
    ECSServiceSecrets,
    ECSServiceDockerExec,
    ECSServiceSSH,
    ECSServiceStandaloneTasks,
    ECSServiceTunnel,
    ECSStandaloneTask,
    ECSStandaloneTaskLogs,
    ECSStandaloneTaskSecrets,
    Logs,
    LogsCloudWatchLogGroup,
    LogsCloudWatchLogStream,
    Tunnels,
)
from .core.aws import build_boto3_session
from .exceptions import DeployfishAppError

# configuration defaults
CONFIG = init_defaults('deployfish')
META = init_defaults('log.logging')
META['log.logging']['log_level_argument'] = ['-l', '--level']


def post_arg_parse_build_boto3_session(app: "DeployfishApp") -> None:
    """
    After parsing arguments but before doing any other actions, build a properly
    configured ``boto3.session.Session`` object for us to use in our AWS work.

    Args:
        app: our DeployfishApp object
    """
    app.log.debug('building boto3 session')
    build_boto3_session(
        app.pargs.deployfish_filename,
        use_aws_section=not app.pargs.no_use_aws_section
    )

# ------------------
# The cement app
# ------------------

class DeployfishApp(App):
    """Deployfish primary application."""

    class Meta:
        label = 'deployfish'

        config_defaults = CONFIG
        meta_defaults = META

        # call sys.exit() on close
        exit_on_close = True

        # load additional framework extensions
        extensions = [
            # cement extensions
            'yaml',
            'colorlog',
            'jinja2',
            'print',
            'tabulate',
            # deployfish extensions
            'deployfish.ext.ext_df_argparse',
            'deployfish.ext.ext_df_jinja2',
            'deployfish.ext.ext_df_plugin',
        ]

        # configuration handler
        config_handler = 'yaml'

        # configuration file suffix
        config_file_suffix = '.yml'

        # handlers
        log_handler = 'colorlog'
        output_handler = 'df_jinja2'
        plugin_handler = 'df_plugin'

        # where do our templates live?
        template_module = 'deployfish.templates'
        # how do we want to render our templates?
        template_handler = 'df_jinja2'

        # register handlers
        handlers = [
            Base,
            BaseService,
            BaseServiceSecrets,
            BaseServiceSSH,
            BaseServiceDockerExec,
            BaseTunnel,
            EC2ClassicLoadBalancer,
            EC2LoadBalancer,
            EC2LoadBalancerListener,
            EC2LoadBalancerTargetGroup,
            ECSCluster,
            ECSClusterSSH,
            ECSInvokedTask,
            ECSService,
            ECSServiceCommands,
            ECSServiceCommandLogs,
            ECSServiceDockerExec,
            ECSServiceSecrets,
            ECSServiceSSH,
            ECSServiceStandaloneTasks,
            ECSServiceTunnel,
            ECSStandaloneTask,
            ECSStandaloneTaskLogs,
            ECSStandaloneTaskSecrets,
            Logs,
            LogsCloudWatchLogGroup,
            LogsCloudWatchLogStream,
            Tunnels
        ]

        # define hooks
        define_hooks = [
            'pre_object_create',    # hook(app: App, obj: Model)
            'post_object_create',   # hook(app: App, obj: Model, success: bool = True, reason: str = None)
            'pre_object_update',    # hook(app: App, obj: Model)
            'post_object_update',   # hook(app: App, obj: Model, success: bool = True, reason: str = None)
            'pre_object_delete',    # hook(app: App, obj: Model)
            'post_object_delete',   # hook(app: App, obj: Model, success: bool =  True, reason: str = None)
            'pre_service_scale',     # hook(app: App, obj: Service, count: int)
            'post_service_scale',    # hook(app: App, obj: Service, count: int)
            'pre_service_restart',   # hook(app: App, obj: Service)
            'post_service_restart',  # hook(app: App, obj: Service)
            'pre_cluster_scale',     # hook(app: App, obj: Cluster, count: int)
            'post_cluster_scale',    # hook(app: App, obj: Cluster, count: int)
        ]

        # register hooks
        hooks = [
            ('post_argument_parsing', post_arg_parse_build_boto3_session)
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._deployfish_config: Optional[Config] = None
        self._raw_deployfish_config: Optional[Config] = None

    @property
    def deployfish_config(self) -> Config:
        """
        Lazy load the ``deployfish.yml`` file.  We only load it on request because most
        deployfish commands don't need it.

        Returns:
            The fully interpolated Config object.
        """
        if not self._deployfish_config:
            ignore_missing_environment = False
            if (
                self.pargs.ignore_missing_environment or
                os.environ.get('DEPLOYFISH_IGNORE_MISSING_ENVIRONMENT', 'false').lower() == 'true'
            ):
                ignore_missing_environment = True
            config_kwargs: Dict[str, Any] = {
                'filename': self.pargs.deployfish_filename,
                'env_file': self.pargs.env_file,
                'tfe_token': self.pargs.tfe_token,
                'ignore_missing_environment': ignore_missing_environment
            }
            self._deployfish_config = Config.new(**config_kwargs)
        return self._deployfish_config

    @property
    def raw_deployfish_config(self) -> Config:
        """
        Lazy load the ``deployfish.yml`` file into a ``Config`` object, but don't run any
        interpolations.

        Returns:
            The un-interpolated Config object.
        """
        if not self._raw_deployfish_config:
            config_kwargs: Dict[str, Any] = {
                'filename': self.pargs.deployfish_filename,
                'ignore_missing_environment': True,
                'interpolate': False
            }
            self._raw_deployfish_config = Config.new(**config_kwargs)
        return self._raw_deployfish_config


# ==========================================
# entrypoint
# ==========================================


def main():
    with DeployfishApp() as app:
        set_app(app)
        try:
            app.run()

        except AssertionError as e:
            print('AssertionError > %s' % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except DeployfishAppError as e:
            print('DeployfishAppError > %s' % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print('\n%s' % e)
            app.exit_code = 0


if __name__ == '__main__':
    main()
