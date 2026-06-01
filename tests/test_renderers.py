from unittest.mock import MagicMock

import pytest
from deployfish.exceptions import RenderException
from deployfish.renderers.misc import target_group_listener_rules
from deployfish.renderers.table import TableRenderer


class TestTableRenderer:
    def test_render_simple_rows(self) -> None:
        row = type("Row", (), {"name": "alpha", "count": 3})()
        renderer = TableRenderer({"Name": "name", "Count": "count"}, ordering="Name")
        output = renderer.render([row])
        assert "alpha" in output
        assert "3" in output

    def test_render_timestamp_column_with_epoch(self) -> None:
        row = type("Row", (), {"created": 1_704_110_400_000})()
        renderer = TableRenderer(
            {
                "Created": {
                    "key": "created",
                    "datatype": "timestamp",
                }
            }
        )
        output = renderer.render([row])
        assert "2024" in output or "2023" in output

    def test_render_missing_required_field_raises(self) -> None:
        row = {"name": "only-dict-keys"}
        renderer = TableRenderer({"Name": "missing_key"})
        with pytest.raises(RenderException):
            renderer.render([row])


class TestMiscRenderer:
    def test_target_group_listener_rules_with_conditions(self) -> None:
        tg = MagicMock()
        rule = MagicMock()
        rule.data = {
            "Conditions": [
                {"PathPatternConfig": {"Values": ["/api/*"]}},
            ]
        }
        tg.rules = [rule]
        result = target_group_listener_rules(tg)
        assert "path:/api/*" in result
