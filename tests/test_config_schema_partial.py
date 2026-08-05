"""Tests for deployfish.config.schema._partial.partial_model."""

import pytest
from deployfish.config.schema._partial import partial_model
from pydantic import BaseModel, ValidationError, field_validator


class _Widget(BaseModel):
    name: str
    count: int = 1

    @field_validator("count")
    @classmethod
    def _count_must_be_positive(cls, value: int) -> int:
        if value < 1:
            msg = "count must be positive"
            raise ValueError(msg)
        return value


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

    def test_inherited_validators_still_run_when_value_given(self) -> None:
        Partial = partial_model(_Widget)  # noqa: N806
        with pytest.raises(ValidationError, match="count must be positive"):
            Partial(count=0)

    def test_inherited_validators_skipped_when_value_omitted(self) -> None:
        Partial = partial_model(_Widget)  # noqa: N806
        instance = Partial(name="thing")
        assert instance.name == "thing"
        assert instance.count is None
