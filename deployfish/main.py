# pylint: disable=import-outside-toplevel
import contextlib
import os
import sys
from typing import Any

import debugpy
import click
from botocore.exceptions import UnauthorizedSSOTokenError
from cement import App, init_defaults
from cement.core.exc import CaughtSignal

import deployfish.core.adapters  # noqa: F401  # pylint:disable=unused-import

from .config import Config, set_app
from .controllers import (
    Base,
    BaseService,
    BaseServiceDockerExec,
    BaseServiceSecrets,
    BaseServiceSSH,
    BaseTunnel,
    EC2ClassicLoadBalancer,
    EC2LoadBalancer,
    EC2LoadBalancerListener,
    EC2LoadBalancerTargetGroup,
    ECSCluster,
    ECSClusterSSH,
    ECSInvokedTask,
    ECSService,
    ECSServiceCommandLogs,
    ECSServiceCommands,
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
    RDSRDSInstance,
    Tunnels,
)
from .core.aws import build_boto3_session
from .exceptions import DeployfishAppError

# configuration defaults
CONFIG = init_defaults("deployfish")
CONFIG["deployfish"]["ssh_provider"] = os.environ.get("DEPLOYFISH_SSH_PROVIDER", "ssm")
META = init_defaults("log.logging")
META["log.logging"]["log_level_argument"] = ["-l", "--level"]


def post_arg_parse_build_boto3_session(app: "DeployfishApp") -> None:
    """
    After parsing arguments but before doing any other actions, build a properly
    configured ``boto3.session.Session`` object for us to use in our AWS work.

    Args:
        app: our DeployfishApp object

    """
    app.log.debug("building boto3 session")
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
        label = "deployfish"

        config_defaults = CONFIG
        meta_defaults = META

        # call sys.exit() on close
        exit_on_close = True

        # load additional framework extensions
        extensions = [
            # cement extensions
            "yaml",
            "colorlog",
            "jinja2",
            "print",
            "tabulate",
            # deployfish extensions
            "deployfish.ext.ext_df_argparse",
            "deployfish.ext.ext_df_jinja2",
            "deployfish.ext.ext_df_plugin",
        ]

        # configuration handler
        config_handler = "yaml"

        # configuration file suffix
        config_file_suffix = ".yml"

        # handlers
        log_handler = "colorlog"
        output_handler = "df_jinja2"

        # where do our templates live?
        template_module = "deployfish.templates"
        # how do we want to render our templates?
        template_handler = "df_jinja2"

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
            RDSRDSInstance,
            Tunnels
        ]

        # define hooks
        define_hooks = [
            "pre_config_interpolate",    # hook(app: App, obj: Type[Config])
            "pre_object_create",         # hook(app: App, obj: Model)
            "post_object_create",        # hook(app: App, obj: Model, success: bool = True, reason: str = None)
            "pre_object_update",         # hook(app: App, obj: Model)
            "post_object_update",        # hook(app: App, obj: Model, success: bool = True, reason: str = None)
            "pre_object_delete",         # hook(app: App, obj: Model)
            "post_object_delete",        # hook(app: App, obj: Model, success: bool =  True, reason: str = None)
            "pre_service_scale",         # hook(app: App, obj: Service, count: int)
            "post_service_scale",        # hook(app: App, obj: Service, count: int)
            "pre_service_restart",       # hook(app: App, obj: Service)
            "post_service_restart",      # hook(app: App, obj: Service)
            "pre_cluster_scale",         # hook(app: App, obj: Cluster, count: int)
            "post_cluster_scale",        # hook(app: App, obj: Cluster, count: int)
        ]

        # register hooks
        hooks = [
            ("post_argument_parsing", post_arg_parse_build_boto3_session)
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._deployfish_config: Config | None = None
        self._raw_deployfish_config: Config | None = None

    @property
    def deployfish_config(self) -> Config:
        """
        Lazy load the deployfish.yml file.  We only load it on request
        because most deployfish commands don't need it.

        Returns:
            The fully interpolated :py:class:`deployfish.config.Config` object.

        """
        # Allow our plugins to modify Config before our import
        for _ in self.hook.run("pre_config_interpolate", self, Config):
            pass
        if not self._deployfish_config:
            ignore_missing_environment = False
            if (
                self.pargs.ignore_missing_environment or
                os.environ.get("DEPLOYFISH_IGNORE_MISSING_ENVIRONMENT", "false").lower() == "true"
            ):
                ignore_missing_environment = True
            config_kwargs: dict[str, Any] = {
                "filename": self.pargs.deployfish_filename,
                "env_file": self.pargs.env_file,
                "tfe_token": self.pargs.tfe_token,
                "ignore_missing_environment": ignore_missing_environment
            }
            self._deployfish_config = Config.new(**config_kwargs)
            if "proxy" not in self._deployfish_config.get_global_config("ssh"):
                self._deployfish_config.ssh_provider_type = self.config.get("deployfish", "ssh_provider")
        return self._deployfish_config

    @property
    def raw_deployfish_config(self) -> Config:
        """
        Lazy load the deployfish.yml file into a
        :py:class:`deployfish.config.Config` object, but don't run any
        interpolations.

        Returns:
            The un-interpolated Config object.

        """
        if not self._raw_deployfish_config:
            config_kwargs: dict[str, Any] = {
                "filename": self.pargs.deployfish_filename,
                "ignore_missing_environment": True,
                "interpolate": False
            }
            self._raw_deployfish_config = Config.new(**config_kwargs)
        return self._raw_deployfish_config


# ==========================================
# entrypoint
# ==========================================


def main():
    maybe_do_cli_debugging(sys.argv)

    with DeployfishApp() as app:
        set_app(app)
        try:
            app.run()

        except AssertionError as e:
            print("AssertionError > %s" % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except UnauthorizedSSOTokenError as ex:
            click.secho(str(ex), fg="red")
            app.exit_code = 1

        except DeployfishAppError as e:
            print("DeployfishAppError > %s" % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print("\n%s" % e)
            app.exit_code = 0


def maybe_do_cli_debugging(argv):
    """
    Call this to enable client-style debugging of a python script if the user
    passed --debugpy on the command line (can't use --debug because Cement uses it).

    See here for how to set up VSCode to act as a remote debug server:
    https://access.caltech.edu/caltech_docs/docs/project/ads-handbook/latest/local_development/debugging_python_with_vscode/

    This function will use the REMOTE_DEBUG_HOST and REMOTE_DEBUG_PORT env vars to
    to connect to a remote debug server. They default to "localhost" and 5678,
    respectively.

    Args:
        argv: Pass sys.argv here for us to check for the --debugpy flag.
              That flag will be removed if present.

    """
    if "--debugpy" in argv:
        try:
            # Redirect stderr to /dev/null to avoid printing debugpy's error message.
            # We have our own.
            with open(os.devnull, "w") as devnull, contextlib.redirect_stderr(devnull):
                debugpy.connect(("localhost", 5678))
        except ConnectionRefusedError:
            print("No debug server is running at localhost:5678.")
        else:
            print("Connected to debug server at localhost:5678.")
        # Remove the --debug flag because django will complain about it.
        argv.remove("--debugpy")


if __name__ == "__main__":
    main()
