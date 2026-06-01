import sys
from unittest.mock import MagicMock, patch

from botocore.exceptions import UnauthorizedSSOTokenError
from cement.core.exc import CaughtSignal
from deployfish.exceptions import DeployfishAppError

DEBUGPY = MagicMock()


class TestMainHooks:
    def test_post_arg_parse_builds_boto3_session(self) -> None:
        debugpy = MagicMock()
        with patch.dict(sys.modules, {"debugpy": debugpy}):
            from deployfish.main import post_arg_parse_build_boto3_session

            app = MagicMock()
            app.pargs.deployfish_filename = "deployfish.yml"
            app.pargs.no_use_aws_section = False
            app.log = MagicMock()
            with patch("deployfish.main.build_boto3_session") as build_mock:
                post_arg_parse_build_boto3_session(app)
            build_mock.assert_called_once_with("deployfish.yml", use_aws_section=True)


class TestMainEntrypoint:
    def test_main_handles_sso_token_error(self) -> None:
        with patch.dict(sys.modules, {"debugpy": DEBUGPY}):
            from deployfish.main import main

            app = MagicMock()
            app.run.side_effect = UnauthorizedSSOTokenError(
                error_response={"Error": {"Message": "SSO token expired"}},
                operation_name="GetCallerIdentity",
            )
            with patch("deployfish.main.DeployfishApp") as app_cls:
                app_cls.return_value.__enter__.return_value = app
                app_cls.return_value.__exit__.return_value = False
                with patch("deployfish.main.set_app"):
                    with patch("deployfish.main.maybe_do_cli_debugging"):
                        with patch("deployfish.main.click.secho") as secho_mock:
                            main()
            secho_mock.assert_called_once()
            assert app.exit_code == 1

    def test_main_caught_signal_exits_cleanly(self, capsys) -> None:
        with patch.dict(sys.modules, {"debugpy": DEBUGPY}):
            from deployfish.main import main

            app = MagicMock()
            app.run.side_effect = CaughtSignal(signum=2, frame=None)
            with patch("deployfish.main.DeployfishApp") as app_cls:
                app_cls.return_value.__enter__.return_value = app
                app_cls.return_value.__exit__.return_value = False
                with patch("deployfish.main.set_app"):
                    with patch("deployfish.main.maybe_do_cli_debugging"):
                        main()
            assert app.exit_code == 0
            assert "Caught signal" in capsys.readouterr().out

    def test_main_handles_deployfish_app_error(self) -> None:
        with patch.dict(sys.modules, {"debugpy": DEBUGPY}):
            from deployfish.main import main

            app = MagicMock()
            app.run.side_effect = DeployfishAppError("configuration failed")
            app.debug = False
            with patch("deployfish.main.DeployfishApp") as app_cls:
                app_cls.return_value.__enter__.return_value = app
                app_cls.return_value.__exit__.return_value = False
                with patch("deployfish.main.set_app"):
                    with patch("deployfish.main.maybe_do_cli_debugging"):
                        with patch("builtins.print") as print_mock:
                            main()
            print_mock.assert_called()
            assert app.exit_code == 1

    def test_deployfish_app_meta_registers_controllers(self) -> None:
        with patch.dict(sys.modules, {"debugpy": DEBUGPY}):
            from deployfish.main import DeployfishApp

            assert DeployfishApp.Meta.label == "deployfish"
            assert "deployfish.ext.ext_df_plugin" in DeployfishApp.Meta.extensions


class TestMaybeDoCliDebugging:
    def test_debugpy_flag_removed_from_argv(self) -> None:
        with patch.dict(sys.modules, {"debugpy": DEBUGPY}):
            from deployfish.main import maybe_do_cli_debugging

            argv = ["deploy", "--debugpy", "service", "list"]
            DEBUGPY.connect.return_value = None
            with patch("builtins.print"):
                maybe_do_cli_debugging(argv)
            assert "--debugpy" not in argv
