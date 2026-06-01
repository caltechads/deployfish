from pathlib import Path
from unittest.mock import patch

from deployfish.config.config import Config

from tests.fixtures import SERVICE_YML


class TestConfigModule:
    def test_config_loads_services_section(self, tmp_path: Path) -> None:
        yml = tmp_path / "deployfish.yml"
        yml.write_text(
            "services:\n"
            "  - name: foobar-test\n"
            "    cluster: foobar-cluster\n"
            "    count: 1\n"
            "    family: foobar-test\n"
            "    network_mode: host\n"
            "    task_role_arn: arn:role\n"
            "    containers:\n"
            "      - name: foobar\n"
            "        image: foobar/foobar:0.1.0\n"
            "        cpu: 512\n"
            "        memory: 512\n",
            encoding="utf-8",
        )
        with patch(
            "deployfish.config.processors.terraform.TerraformStateConfigProcessor.replace",
            side_effect=lambda obj, key, value, *args, **kwargs: (
                setattr(obj, key, value) or value
            ),
        ):
            config = Config.new(filename=str(yml), interpolate=False)
        item = config.get_raw_section_item("services", "foobar-test")
        assert item["name"] == "foobar-test"

    def test_get_section_item_from_fixture_shape(
        self, minimal_deployfish_yml: Path
    ) -> None:
        with patch(
            "deployfish.config.processors.terraform.TerraformStateConfigProcessor.replace",
            side_effect=lambda obj, key, value, *args, **kwargs: (
                setattr(obj, key, value) or value
            ),
        ):
            config = Config.new(filename=str(minimal_deployfish_yml), interpolate=False)
        item = config.get_section_item("services", "foobar-test")
        assert item["cluster"] == SERVICE_YML["cluster"]
