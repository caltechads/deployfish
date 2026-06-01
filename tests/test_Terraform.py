import json
from pathlib import Path
from unittest.mock import Mock, patch

from deployfish.config.processors.terraform import TerraformS3State

TESTS_DIR = Path(__file__).parent

YAML = {
    "statefile": "s3://foobar/baz",
    "lookups": {
        "lookup1": "{environment}-cluster-name",
        "lookup2": "{environment}-elb-id",
        "lookup3": "{environment}-autoscalinggroup-name",
        "lookup4": "security-group-list",
    },
}


class TestTerraform_load_yaml:
    def setup_method(self) -> None:
        self.terraform = TerraformS3State(YAML, {})

    def test_lookups(self) -> None:
        assert self.terraform.terraform_config["lookups"] == {
            "lookup1": "{environment}-cluster-name",
            "lookup2": "{environment}-elb-id",
            "lookup3": "{environment}-autoscalinggroup-name",
            "lookup4": "security-group-list",
        }


class TestTerraform_get_terraform_state:
    def setup_method(self) -> None:
        with (TESTS_DIR / "terraform.tfstate").open(encoding="utf-8") as f:
            self.tfstate = json.loads(f.read())
        self.terraform = TerraformS3State(YAML, {})

    def test_lookup(self) -> None:
        with patch(
            "deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3",
            Mock(return_value=self.tfstate),
        ):
            self.terraform.load({"environment": "qa"})
        assert "qa-cluster-name" in self.terraform.terraform_lookups


class TestTerraform_get_terraform_state_v12:
    def setup_method(self) -> None:
        with (TESTS_DIR / "terraform.tfstate.0.12").open(encoding="utf-8") as f:
            self.tfstate = json.loads(f.read())
        self.terraform = TerraformS3State(YAML, {})

    def test_lookup(self) -> None:
        with patch(
            "deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3",
            Mock(return_value=self.tfstate),
        ):
            self.terraform.load({"environment": "qa"})
        assert "prod-rds-address" in self.terraform.terraform_lookups


class TestTerraform_lookup:
    def setup_method(self) -> None:
        with (TESTS_DIR / "terraform.tfstate").open(encoding="utf-8") as f:
            self.tfstate = json.loads(f.read())
        self.terraform = TerraformS3State(YAML, {})

    def test_lookup(self) -> None:
        with patch(
            "deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3",
            Mock(return_value=self.tfstate),
        ):
            self.terraform.load({"environment": "qa"})
        assert self.terraform.lookup("lookup1", {"{environment}": "qa"}) == "foobar-cluster-qa"
        assert self.terraform.lookup("lookup1", {"{environment}": "prod"}) == "foobar-cluster-prod"
        assert self.terraform.lookup("lookup4", {}) == [
            "sg-1234567",
            "sg-2345678",
            "sg-3456789",
        ]
