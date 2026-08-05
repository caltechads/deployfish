"""
Helper for deriving "partial update" Pydantic models, used for the ``partial``
(overlay) construction mode our adapters support.
"""

import copy
import typing
from typing import Any

from pydantic import BaseModel, create_model


def partial_model(
    model: type[BaseModel],
    name: str | None = None,
    nested: dict[str, type[BaseModel]] | None = None,
) -> type[BaseModel]:
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

    ``nested`` opts specific fields into also swapping their nested model
    type for a caller-supplied partial variant, instead of just unioning the
    field's existing annotation with ``None``. Without this, a
    ``list[SomeModel]`` field would become ``list[SomeModel] | None`` --
    the list itself becomes optional, but entries inside it stay the
    *strict* ``SomeModel``, rejecting partial entries. This is opt-in per
    field (not automatic for every ``list[BaseModel]``/``BaseModel`` field)
    so existing callers -- e.g. ``ContainerDefinitionOverlayInput`` --
    keep their exact current behavior unless they explicitly ask for more.

    Args:
        model: the strict model to derive the partial variant from.

    Keyword Args:
        name: the name to give the new model class. Defaults to
            ``f"Partial{model.__name__}"``.
        nested: a ``{field_name: partial_variant}`` map. For each named
            field, use ``partial_variant`` as the field's (or its list
            entries') type instead of the field's original nested model
            type.

    Returns:
        A new model class, subclassing ``model``, with every field optional.

    """
    # Use get_type_hints (not __annotations__) so inherited/composed models
    # still resolve Annotated types with their metadata intact.
    type_hints = typing.get_type_hints(model, include_extras=True)
    nested = nested or {}

    field_overrides: dict[str, Any] = {}
    for field_name, field_info in model.model_fields.items():
        original_annotation = type_hints.get(field_name, field_info.annotation)

        if field_name in nested:
            replacement = nested[field_name]
            origin = typing.get_origin(original_annotation)
            effective_annotation: Any = (
                list[replacement] if origin is list else replacement  # type: ignore[valid-type]
            )
        else:
            effective_annotation = original_annotation

        # Make it optional by unioning with None
        optional_annotation = (
            effective_annotation | None
            if effective_annotation is not None
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
