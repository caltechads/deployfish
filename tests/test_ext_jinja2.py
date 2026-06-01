from datetime import datetime
from unittest.mock import patch

from deployfish.ext.ext_df_jinja2 import (
    color,
    fromtimestamp,
    lb_listener_table,
    section_title,
    tabular,
    target_group_listener_rules,
    target_group_table,
)
from deployfish.renderers import LBListenerTableRenderer, TargetGroupTableRenderer


class TestJinjaFilters:
    def test_color_wraps_value(self) -> None:
        result = color("hello", fg="green")
        assert "hello" in result

    def test_section_title_renders_header(self) -> None:
        result = section_title("Services")
        assert "Services" in result
        assert "-" in result

    def test_fromtimestamp_epoch_seconds(self) -> None:
        result = fromtimestamp(datetime(2026, 1, 1, 12, 0, 0).timestamp())
        assert "2026-01-01" in result

    def test_fromtimestamp_milliseconds(self) -> None:
        result = fromtimestamp(1_700_000_000_000)
        assert "2026" in result or "2023" in result

    def test_tabular_renders_rows(self) -> None:
        row = type("Row", (), {"name": "svc-a", "count": 2})()
        result = tabular([row], Name="name", Count="count")
        assert "svc-a" in result
        assert "2" in result

    def test_target_group_table_renders(self) -> None:
        row = type(
            "Row",
            (),
            {
                "name": "tg-a",
                "listener_port": 443,
                "rules": "path:/",
                "container_port": 8080,
                "targets": 2,
            },
        )()
        with patch.object(TargetGroupTableRenderer, "render", return_value="table-output"):
            assert target_group_table([row]) == "table-output"

    def test_lb_listener_table_renders(self) -> None:
        row = type(
            "Row",
            (),
            {
                "port": 443,
                "protocol": "HTTPS",
                "default_action": "forward",
                "rules": 1,
                "certificates": "cert",
            },
        )()
        with patch.object(LBListenerTableRenderer, "render", return_value="listeners"):
            assert lb_listener_table([row]) == "listeners"

    def test_target_group_listener_rules_host_header(self) -> None:
        tg = type("TG", (), {})()
        rule = type("Rule", (), {})()
        rule.data = {"Conditions": [{"HostHeaderConfig": {"Values": ["api.example.com"]}}]}
        tg.rules = [rule]
        result = target_group_listener_rules(tg)
        assert "hostname:api.example.com" in result
