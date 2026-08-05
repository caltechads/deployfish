"""Tests for deployfish.config.schema._partial.partial_model."""

import pytest
from deployfish.config.schema._partial import partial_model
from pydantic import BaseModel, ValidationError


class _Widget(BaseModel):
    name: str
    count: int = 1


class _Gadget(BaseModel):
    name: str
    tags: list[str] = []


class _WidgetContainer(BaseModel):
    name: str
    widgets: list[_Widget] = []
    gadget: _Gadget | None = None


class TestPartialModel:
    def test_all_fields_become_optional(self) -> None:
        Partial = partial_model(_Widget)  # noqa: N806
        instance = Partial()
        assert instance.name is None
        assert instance.count is None

    def test_default_name_is_Partial_prefixed(self) -> None:  # noqa: N802
        Partial = partial_model(_Widget)  # noqa: N806
        assert Partial.__name__ == "PartialWidget"

    def test_custom_name(self) -> None:
        Partial = partial_model(_Widget, name="WidgetOverlay")  # noqa: N806
        assert Partial.__name__ == "WidgetOverlay"

    def test_all_fields_optional_with_provided_values(self) -> None:
        Partial = partial_model(_Widget)  # noqa: N806
        test_count = 5
        instance = Partial(name="thing", count=test_count)
        assert instance.name == "thing"
        assert instance.count == test_count

    def test_omitted_fields_default_to_none(self) -> None:
        Partial = partial_model(_Widget)  # noqa: N806
        instance = Partial(name="thing")
        assert instance.name == "thing"
        assert instance.count is None


class TestPartialModelNested:
    def test_list_field_not_in_nested_keeps_strict_inner_type(self) -> None:
        Partial = partial_model(_WidgetContainer)  # noqa: N806
        with pytest.raises(ValidationError):
            # widgets entries are still strict _Widget: name is required
            Partial(widgets=[{"count": 0}])

    def test_list_field_in_nested_uses_partial_inner_type(self) -> None:
        PartialWidget = partial_model(_Widget)  # noqa: N806
        Partial = partial_model(  # noqa: N806
            _WidgetContainer, nested={"widgets": PartialWidget}
        )
        instance = Partial(widgets=[{"count": 0}])
        assert instance.widgets[0].name is None
        assert instance.widgets[0].count == 0

    def test_scalar_field_in_nested_uses_partial_inner_type(self) -> None:
        PartialGadget = partial_model(_Gadget)  # noqa: N806
        Partial = partial_model(  # noqa: N806
            _WidgetContainer, nested={"gadget": PartialGadget}
        )
        instance = Partial(gadget={"tags": ["x"]})
        assert instance.gadget.name is None
        assert instance.gadget.tags == ["x"]

    def test_field_not_named_in_nested_is_unaffected_by_sibling_nesting(self) -> None:
        PartialWidget = partial_model(_Widget)  # noqa: N806
        Partial = partial_model(  # noqa: N806
            _WidgetContainer, nested={"widgets": PartialWidget}
        )
        instance = Partial()
        assert instance.name is None
