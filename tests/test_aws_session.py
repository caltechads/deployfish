from unittest.mock import MagicMock, patch

import pytest
from deployfish.core import aws as aws_module
from deployfish.core.aws import (
    AWSSessionBuilder,
    build_boto3_session,
    get_boto3_session,
)
from deployfish.exceptions import ConfigProcessingFailed


class TestAWSSessionBuilderLoadConfig:
    def test_load_config_missing_file_returns_empty(self, tmp_path) -> None:
        builder = AWSSessionBuilder()
        assert builder.load_config(str(tmp_path / "missing.yml")) == {}

    def test_load_config_unreadable_raises(self, tmp_path) -> None:
        config_path = tmp_path / "deployfish.yml"
        config_path.write_text("aws:\n  profile: test\n", encoding="utf-8")
        builder = AWSSessionBuilder()
        with patch("deployfish.core.aws.os.access", return_value=False):
            with pytest.raises(ConfigProcessingFailed, match="not readable"):
                builder.load_config(str(config_path))

    def test_load_config_reads_yaml(self, tmp_path) -> None:
        config_path = tmp_path / "deployfish.yml"
        config_path.write_text("aws:\n  region: us-west-2\n", encoding="utf-8")
        builder = AWSSessionBuilder()
        assert builder.load_config(str(config_path)) == {"aws": {"region": "us-west-2"}}


class TestAWSSessionBuilderNew:
    def test_no_such_aws_profile(self, tmp_path) -> None:
        config_path = tmp_path / "deployfish.yml"
        config_path.write_text("aws:\n  profile: missing-profile\n", encoding="utf-8")
        builder = AWSSessionBuilder()
        with patch("deployfish.core.aws.boto3.session.Session") as session_cls:
            session_cls.return_value.available_profiles = ["default"]
            with pytest.raises(AWSSessionBuilder.NoSuchAWSProfile, match="missing-profile"):
                builder.new(str(config_path))

    def test_forbidden_account_id_raises(self, tmp_path) -> None:
        config_path = tmp_path / "deployfish.yml"
        config_path.write_text(
            "aws:\n  forbidden_account_ids:\n    - '111111111111'\n",
            encoding="utf-8",
        )
        builder = AWSSessionBuilder()
        session = MagicMock()
        session.client.return_value.get_caller_identity.return_value = {"Account": "111111111111"}
        with patch.object(
            AWSSessionBuilder,
            "_AWSSessionBuilder__get_boto3_session",
            return_value=session,
        ), pytest.raises(AWSSessionBuilder.ForbiddenAWSAccountId):
            builder.new(str(config_path))

    def test_allowed_account_id_passes(self, tmp_path) -> None:
        config_path = tmp_path / "deployfish.yml"
        config_path.write_text(
            "aws:\n  allowed_account_ids:\n    - '222222222222'\n",
            encoding="utf-8",
        )
        builder = AWSSessionBuilder()
        session = MagicMock()
        session.client.return_value.get_caller_identity.return_value = {"Account": "222222222222"}
        with patch.object(
            AWSSessionBuilder,
            "_AWSSessionBuilder__get_boto3_session",
            return_value=session,
        ):
            assert builder.new(str(config_path)) is session


class TestBuildBoto3Session:
    def test_build_boto3_session_sets_global(self, tmp_path) -> None:
        config_path = tmp_path / "deployfish.yml"
        config_path.write_text("aws:\n  region: us-east-1\n", encoding="utf-8")
        session = MagicMock()
        aws_module.boto3_session = None
        with patch.object(AWSSessionBuilder, "new", return_value=session):
            build_boto3_session(str(config_path))
        assert aws_module.boto3_session is session

    def test_get_boto3_session_uses_override(self) -> None:
        override = MagicMock()
        assert get_boto3_session(boto3_session_override=override) is override
