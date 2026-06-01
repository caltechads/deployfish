from unittest.mock import patch

from deployfish.ext.ext_df_jinja2 import tabular, target_group_listener_rules
from deployfish.renderers import TableRenderer


class TestTabularExtended:
    def test_tabular_with_datatype_and_default_kwargs(self) -> None:
        row = type("Row", (), {"created": 1_735_732_800_000})()
        output = tabular(
            [row],
            Created="created",
            Created_datatype="timestamp",
            ordering="Created",
        )
        assert "2025" in output or "2026" in output

    def test_target_group_listener_rules_path_and_header(self) -> None:
        tg = type("TG", (), {})()
        rule = type("Rule", (), {})()
        rule.data = {
            "Conditions": [
                {"PathPatternConfig": {"Values": ["/api/*"]}},
                {
                    "HttpHeaderConfig": {
                        "HttpHeaderName": "X-Custom",
                        "Values": ["abc"],
                    }
                },
            ]
        }
        tg.rules = [rule]
        result = target_group_listener_rules(tg)
        assert "path:/api/*" in result
        assert "header:X-Custom" in result

    def test_tabular_with_default_column(self) -> None:
        row = {"name": "alpha"}
        with patch.object(
            TableRenderer, "render", return_value="rendered"
        ) as render_mock:
            assert tabular([row], Name="name", Name_default="n/a") == "rendered"
        assert render_mock.called
