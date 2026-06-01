import sys
from unittest.mock import MagicMock, patch


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
