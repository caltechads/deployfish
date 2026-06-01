import errno
import os
from unittest.mock import MagicMock, patch

import pytest
from deployfish.config.processors.abstract import AbstractConfigProcessor
from deployfish.config.processors.environment import EnvironmentConfigProcessor
from deployfish.config.processors.terraform import (
    AbstractTerraformState,
    TerraformEnterpriseState,
)
from deployfish.exceptions import ConfigProcessingFailed


class TestEnvironmentConfigProcessor:
    def test_missing_env_file_raises_by_default(self) -> None:
        config = MagicMock()
        with pytest.raises(AbstractConfigProcessor.ProcessingFailed, match="does not exist"):
            EnvironmentConfigProcessor(
                config,
                {"env_file": "/no/such/env_file.env"},
            )

    def test_ignore_missing_environment_skips_missing_file(self) -> None:
        config = MagicMock()
        processor = EnvironmentConfigProcessor(
            config,
            {
                "env_file": "/no/such/env_file.env",
                "ignore_missing_environment": True,
            },
        )
        assert processor._load_env_file("/no/such/env_file.env") == {}

    def test_unreadable_env_file_raises(self, tmp_path) -> None:
        env_path = tmp_path / "secrets.env"
        env_path.write_text("KEY=value\n", encoding="utf-8")
        config = MagicMock()
        processor = EnvironmentConfigProcessor(config, {})
        with patch("builtins.open", side_effect=OSError(errno.EACCES, "Permission denied")):
            with pytest.raises(AbstractConfigProcessor.ProcessingFailed, match="not readable"):
                processor._load_env_file(str(env_path))

    def test_import_env_merges_os_environ(self, tmp_path) -> None:
        env_path = tmp_path / "secrets.env"
        env_path.write_text("FROM_FILE=value\n", encoding="utf-8")
        config = MagicMock()
        with patch.dict(os.environ, {"FROM_ENV": "env-value"}, clear=False):
            processor = EnvironmentConfigProcessor(
                config,
                {"env_file": str(env_path), "import_env": True},
            )
        assert processor.environ["FROM_FILE"] == "value"
        assert processor.environ["FROM_ENV"] == "env-value"


class TestTerraformEnterpriseState:
    def test_tfe_backend_load(self) -> None:
        tfstate = {
            "modules": [
                {
                    "path": ["root"],
                    "outputs": {
                        "cluster_name": {"value": "prod-cluster"},
                    },
                }
            ]
        }
        terraform_config = {
            "organization": "my-org",
            "workspace": "my-workspace",
            "lookups": {"cluster_name": "cluster_name"},
        }
        with patch.dict(os.environ, {"ATLAS_TOKEN": "test-token"}, clear=True):
            state = object.__new__(TerraformEnterpriseState)
            AbstractTerraformState.__init__(state, terraform_config, {})
            state.api_token = "test-token"
            state.loaded = False
        with patch.object(
            state,
            "get_terraform_state_download_url",
            return_value="https://example.com/state",
        ), patch(
            "deployfish.config.processors.terraform.requests.get",
            return_value=MagicMock(text='{"modules": []}'),
        ) as requests_get:
            requests_get.return_value.text = __import__("json").dumps(tfstate)
            state.load({})
        assert state.terraform_lookups["cluster_name"]["value"] == "prod-cluster"

    def test_tfe_backend_requires_api_token(self) -> None:
        terraform_config = {
            "organization": "my-org",
            "workspace": "my-workspace",
            "lookups": {},
        }
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigProcessingFailed, match="No Terraform Enterprise API token"):
                TerraformEnterpriseState(terraform_config, {})
