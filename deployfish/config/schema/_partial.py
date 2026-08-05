"""
Helper for deriving "partial update" Pydantic models, used for the ``partial``
(overlay) construction mode our adapters support.
"""

from typing import Any, Optional

from pydantic import BaseModel, create_model


def partial_model(model: type[BaseModel], name: str | None = None) -> type[BaseModel]:
    """
    Build a subclass of ``model`` where every field is optional and defaults to
    ``None``.

    Field validators defined on ``model`` are inherited unchanged, because the
    result is a real subclass of ``model``: a validator still runs -- and can
    still raise -- whenever a field is actually given a value, but no longer
    runs (and no error is raised) when the field is omitted.

    Args:
        model: the strict model to derive the partial variant from.

    Keyword Args:
        name: the name to give the new model class. Defaults to
            ``f"Partial{model.__name__}"``.

    Returns:
        A new model class, subclassing ``model``, with every field optional.

    """
    field_overrides: dict[str, Any] = {
        field_name: (Optional[field_info.annotation], None)
        for field_name, field_info in model.model_fields.items()
    }
    model_name = model.__name__.lstrip("_")
    return create_model(
        name or f"Partial{model_name}",
        __base__=model,
        **field_overrides,
    )
