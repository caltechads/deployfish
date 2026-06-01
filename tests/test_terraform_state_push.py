"""Terraform state processor coverage."""

from unittest.mock import patch

import pytest
from deployfish.config.processors.terraform import (
    TerraformS3State,
    TerraformStateFactory,
)
from deployfish.exceptions import SchemaException


class TestTerraformStateFactory:
    def test_new_s3_state(self) -> None:
        state = TerraformStateFactory.new(
            {"statefile": "s3://bucket/terraform.tfstate", "lookups": {}},
            {},
        )
        assert isinstance(state, TerraformS3State)

    def test_new_raises_without_backend(self) -> None:
        with pytest.raises(SchemaException):
            TerraformStateFactory.new({"lookups": {}}, {})


class TestTerraformS3State:
    def test_load_skips_when_replacements_unchanged(self) -> None:
        state = TerraformS3State(
            {"statefile": "s3://bucket/state", "lookups": {"vpc": "vpc_id"}},
            {},
        )
        state.loaded = True
        state.replacements = {"x": "y"}
        with patch.object(state, "_get_state_file_from_s3") as get_mock:
            state.load({"x": "y"})
        get_mock.assert_not_called()
