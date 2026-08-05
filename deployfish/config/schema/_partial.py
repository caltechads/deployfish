"""
Helper for deriving "partial update" Pydantic models, used for the ``partial``
(overlay) construction mode our adapters support.
"""

import copy
import typing
from typing import Any

from pydantic import BaseModel, create_model


def partial_model(model: type[BaseModel], name: str | None = None) -> type[BaseModel]:
    """
    Build a subclass of ``model`` where every field is optional and defaults to
    ``None``.

    Field validators defined on ``model`` are inherited unchanged, because the
    result is a real subclass of ``model``: a validator still runs -- and can
    still raise -- whenever a field is actually given a value, but no longer
    runs (and no error is raised) when the field is omitted.

    Each field's original :py:class:`pydantic.fields.FieldInfo` is copied
    (not rebuilt from scratch), so metadata beyond the annotation --
    ``alias`` in particular -- survives onto the derived model. Without
    this, fields declared with ``Field(alias=...)`` (e.g.
    ``memory_reservation``'s ``"memoryReservation"`` alias) would silently
    lose that alias on the partial variant, and ``extra="forbid"`` would
    then reject the aliased key as an unknown field.

    Args:
        model: the strict model to derive the partial variant from.

    Keyword Args:
        name: the name to give the new model class. Defaults to
            ``f"Partial{model.__name__}"``.

    Returns:
        A new model class, subclassing ``model``, with every field optional.

    """
    # Use get_type_hints (not __annotations__) so inherited/composed models
    # still resolve Annotated types with their metadata intact.
    type_hints = typing.get_type_hints(model, include_extras=True)

    field_overrides: dict[str, Any] = {}
    for field_name, field_info in model.model_fields.items():
        original_annotation = type_hints.get(field_name, field_info.annotation)

        # Make it optional by unioning with None
        optional_annotation = (
            original_annotation | None
            if original_annotation is not None
            else None
        )

        # Copy the original FieldInfo so alias (and any other metadata)
        # survives, rather than building a bare Field(default=None).
        new_field_info = copy.copy(field_info)
        new_field_info.annotation = optional_annotation
        new_field_info.default = None
        new_field_info.default_factory = None

        field_overrides[field_name] = (optional_annotation, new_field_info)

    model_name = model.__name__.lstrip("_")
    return create_model(
        name or f"Partial{model_name}",
        __base__=model,
        **field_overrides,
    )
