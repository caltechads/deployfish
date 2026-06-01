from pathlib import Path
from unittest.mock import patch

from deployfish.config.config import Config


class TestConfigExtended:
    def test_get_section_returns_list(self, minimal_deployfish_yml: Path) -> None:
        with patch(
            "deployfish.config.processors.terraform.TerraformStateConfigProcessor.replace",
            side_effect=lambda obj, key, value, *args, **kwargs: setattr(obj, key, value) or value,
        ):
            config = Config.new(filename=str(minimal_deployfish_yml), interpolate=False)
        section = config.get_section("services")
        assert len(section) == 1
        assert section[0]["name"] == "foobar-test"

    def test_get_raw_section_item(self, minimal_deployfish_yml: Path) -> None:
        with patch(
            "deployfish.config.processors.terraform.TerraformStateConfigProcessor.replace",
            side_effect=lambda obj, key, value, *args, **kwargs: setattr(obj, key, value) or value,
        ):
            config = Config.new(filename=str(minimal_deployfish_yml), interpolate=False)
        item = config.get_raw_section_item("services", "foobar-test")
        assert item["cluster"] == "foobar-cluster"
