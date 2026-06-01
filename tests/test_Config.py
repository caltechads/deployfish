import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, call, patch

from deployfish.config.config import Config

TESTS_DIR = Path(__file__).parent


def statefile_loader(
    state_file_url: str,
    profile: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    if state_file_url == "s3://my-qa-statefile":
        with (TESTS_DIR / "terraform.tfstate.qa").open(encoding="utf-8") as f:
            return json.loads(f.read())
    if state_file_url == "s3://my-prod-statefile":
        with (TESTS_DIR / "terraform.tfstate.prod").open(encoding="utf-8") as f:
            return json.loads(f.read())
    msg = "unknown state file requested"
    raise KeyError(msg)


class TestContainerDefinition_terraform_statefile_interpolation:
    def setup_method(self) -> None:
        config_yml = TESTS_DIR / "terraform_interpolate.yml"
        with patch(
            "deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3",
        ) as get_mock:
            get_mock.side_effect = statefile_loader
            self.get_mock = get_mock
            self.config = Config.new(filename=str(config_yml))

    def test_environment_gets_replaced_for_each_environment(self) -> None:
        calls = [
            call("s3://my-qa-statefile", profile=None, region=None),
            call("s3://my-prod-statefile", profile=None, region=None),
        ]
        self.get_mock.assert_has_calls(calls)

    def test_file_interpolation_gets_values_from_correct_statefile_for_services(
        self,
    ) -> None:
        prod = self.config.get_section_item("services", "foobar-prod")
        assert prod["cluster"] == "foobar-cluster-prod"
        assert prod["load_balancer"]["load_balancer_name"] == "foobar-prod-elb"
        assert (
            prod["task_role_arn"] == "arn:aws:iam::324958023459:role/foobar-prod-task"
        )
        qa = self.config.get_section_item("services", "foobar-qa")
        assert qa["cluster"] == "foobar-cluster-qa"
        assert qa["load_balancer"]["load_balancer_name"] == "foobar-qa-elb"
        assert qa["task_role_arn"] == "arn:aws:iam::324958023459:role/foobar-qa-task"


class TestTunnelDefinition_terraform_interpolation:
    def setup_method(self) -> None:
        config_yml = TESTS_DIR / "terraform_interpolate.yml"
        with patch(
            "deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3",
        ) as get_mock:
            get_mock.side_effect = statefile_loader
            self.get_mock = get_mock
            self.config = Config.new(filename=str(config_yml))

    def test_environment_gets_replaced_for_each_environment(self) -> None:
        calls = [
            call("s3://my-qa-statefile", profile=None, region=None),
            call("s3://my-prod-statefile", profile=None, region=None),
        ]
        self.get_mock.assert_has_calls(calls)

    def test_file_interpolation_gets_values_from_correct_statefile_for_tunnels(
        self,
    ) -> None:
        qa = self.config.get_section_item("tunnels", "mysql-qa")
        assert qa["host"] == "foo-qa.c970jsizrrcy.us-west-2.rds.amazonaws.com"
        assert qa["port"] == "3306"
        prod = self.config.get_section_item("tunnels", "mysql-prod")
        assert prod["host"] == "foo-prod.c970jsizrrcy.us-west-2.rds.amazonaws.com"
        assert prod["port"] == "3306"


class TestContainerDefinition_load_yaml:
    def setup_method(self) -> None:
        state_file = TESTS_DIR / "terraform.tfstate"
        config_yml = TESTS_DIR / "interpolate.yml"
        env_file = TESTS_DIR / "env_file.env"
        with state_file.open(encoding="utf-8") as f:
            tfstate = json.loads(f.read())
        with patch(
            "deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3",
            Mock(return_value=tfstate),
        ):
            self.config = Config.new(filename=str(config_yml), env_file=str(env_file))

    def test_terraform_simple_interpolation(self) -> None:
        assert (
            self.config.get_service("foobar-prod")["cluster"] == "foobar-cluster-prod"
        )

    def test_terraform_nested_dict_interpolation(self) -> None:
        assert (
            self.config.get_service("foobar-prod")["load_balancer"][
                "load_balancer_name"
            ]
            == "foobar-elb-prod"
        )

    def test_terraform_nested_list_interpolation(self) -> None:
        assert (
            self.config.get_service("foobar-prod")["containers"][0]["environment"][2]
            == "SECRETS_BUCKET_NAME=my-config-store"
        )

    def test_terraform_list_output_interpolation(self) -> None:
        assert self.config.get_service("foobar-prod")["vpc_configuration"][
            "security_groups"
        ] == [
            "sg-1234567",
            "sg-2345678",
            "sg-3456789",
        ]

    def test_terraform_map_output_interpolation(self) -> None:
        assert self.config.get_service("output-test")["vpc_configuration"][
            "subnets"
        ] == [
            "subnet-1234567",
        ]
        assert self.config.get_service("output-test")["vpc_configuration"][
            "security_groups"
        ] == [
            "sg-1234567",
        ]
        assert (
            self.config.get_service("output-test")["vpc_configuration"]["public_ip"]
            == "DISABLED"
        )

    def test_environment_simple_interpolation(self) -> None:
        assert self.config.get_service("foobar-prod")["config"][0] == "FOOBAR=hi_mom"
        assert (
            self.config.get_service("foobar-prod")["config"][2]
            == "FOO_BAR_PREFIX=oh_no/test"
        )
        assert (
            self.config.get_service("foobar-prod")["config"][3]
            == "FOO_BAR_SECRET=)(#jlk329!!3$3093%%.__)"
        )


class TestContainerDefinition_load_yaml_no_interpolate:
    def setup_method(self) -> None:
        state_file = TESTS_DIR / "terraform.tfstate"
        config_yml = TESTS_DIR / "interpolate.yml"
        env_file = TESTS_DIR / "env_file.env"
        with state_file.open(encoding="utf-8") as f:
            tfstate = json.loads(f.read())
        with patch(
            "deployfish.config.processors.terraform.TerraformS3State._get_state_file_from_s3",
            Mock(return_value=tfstate),
        ):
            self.config = Config.new(
                filename=str(config_yml),
                env_file=str(env_file),
                interpolate=False,
            )

    def test_simple_interpolation(self) -> None:
        assert (
            self.config.get_service("foobar-prod")["cluster"]
            == "${terraform.cluster_name}"
        )

    def test_nested_dict_interpolation(self) -> None:
        assert (
            self.config.get_service("foobar-prod")["load_balancer"][
                "load_balancer_name"
            ]
            == "${terraform.elb_id}"
        )

    def test_nested_list_interpolation(self) -> None:
        assert (
            self.config.get_service("foobar-prod")["containers"][0]["environment"][2]
            == "SECRETS_BUCKET_NAME=${terraform.secrets_bucket_name}"
        )

    def test_environment_simple_interpolation(self) -> None:
        assert (
            self.config.get_service("foobar-prod")["config"][0]
            == "FOOBAR=${env.FOOBAR_ENV}"
        )
        assert (
            self.config.get_service("foobar-prod")["config"][2]
            == "FOO_BAR_PREFIX=${env.FOO_BAR_PREFIX_ENV}/test"
        )


class TestTunnelParameters_load_yaml:
    def setup_method(self) -> None:
        config_yml = TESTS_DIR / "interpolate.yml"
        env_file = TESTS_DIR / "env_file.env"
        self.config = Config.new(
            filename=str(config_yml),
            env_file=str(env_file),
            interpolate=False,
        )

    def test_tunnel_find_instance(self) -> None:
        yml = self.config.get_section_item("tunnels", "test")
        assert yml["service"] == "foobar-prod"
        assert yml["host"] == "config.DB_HOST"
        assert yml["port"] == 3306
        assert yml["local_port"] == 8888
