import datetime
from unittest.mock import MagicMock

from deployfish.renderers.table import (
    LBListenerTableRenderer,
    TableRenderer,
    TargetGroupTableRenderer,
)


class TestTableRendererExtended:
    def test_render_bytes_column(self) -> None:
        row = type("Row", (), {"size": 2048})()
        renderer = TableRenderer({"Size": {"key": "size", "datatype": "bytes"}})
        output = renderer.render([row])
        assert "Ki" in output or "2.0" in output

    def test_render_float_column(self) -> None:
        row = type("Row", (), {"ratio": 1.23456})()
        renderer = TableRenderer({"Ratio": "ratio"}, float_precision=2)
        output = renderer.render([row])
        assert "1.23" in output

    def test_render_date_column(self) -> None:
        row = type("Row", (), {"day": datetime.date(2026, 1, 15)})()
        renderer = TableRenderer({"Day": "day"}, date_format="%Y-%m-%d")
        output = renderer.render([row])
        assert "2026-01-15" in output

    def test_render_dict_row(self) -> None:
        renderer = TableRenderer({"Name": "name"})
        output = renderer.render([{"name": "from-dict"}])
        assert "from-dict" in output

    def test_render_nested_key(self) -> None:
        inner = type("Inner", (), {"label": "nested"})()
        row = type("Row", (), {"child": inner})()
        renderer = TableRenderer({"Label": "child__label"})
        output = renderer.render([row])
        assert "nested" in output

    def test_render_reverse_ordering(self) -> None:
        rows = [
            type("Row", (), {"name": "beta"})(),
            type("Row", (), {"name": "alpha"})(),
        ]
        renderer = TableRenderer({"Name": "name"}, ordering="-Name")
        output = renderer.render(rows)
        assert output.index("beta") < output.index("alpha")

    def test_render_without_headers(self) -> None:
        row = type("Row", (), {"name": "solo"})()
        renderer = TableRenderer({"Name": "name"}, show_headers=False)
        output = renderer.render([row])
        assert "Name" not in output.split("\n")[0]

    def test_render_length_column(self) -> None:
        row = type("Row", (), {"items": ["a", "b", "c"]})()
        renderer = TableRenderer({"Count": {"key": "items", "length": True}})
        output = renderer.render([row])
        assert "3" in output

    def test_render_default_value(self) -> None:
        renderer = TableRenderer({"Name": {"key": "missing", "default": "n/a"}})
        output = renderer.render([{"other": "x"}])
        assert "n/a" in output


class TestTargetGroupTableRendererExtended:
    def test_render_container_port(self) -> None:
        tg = MagicMock()
        tg.data = {"Protocol": "HTTP", "Port": 8080}
        renderer = TargetGroupTableRenderer({})
        assert renderer.render_container_port_value(tg, "port", "port") == "HTTP:8080"


class TestLBListenerTableRenderer:
    def test_render_rules_count(self) -> None:
        listener = MagicMock()
        listener.rules = [MagicMock(), MagicMock()]
        renderer = LBListenerTableRenderer({})
        assert renderer.render_rules_value(listener, "rules", "rules") == "2"
