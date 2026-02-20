import dataclasses
from typing import Annotated, Any, get_args, get_origin, get_type_hints

from dash_typed_callbacks.markers import _BaseMarker, _is_marker


def _get_annotated_marker(type_hint: Any) -> _BaseMarker | None:
    """Extracts the first marker from an ``Annotated`` type hint's metadata.

    Scans the metadata entries of an ``Annotated[T, ...]`` hint and returns
    the first ``Out``, ``In``, or ``St`` instance found.  Safely handles
    non-``Annotated`` inputs (including ``None``) by returning ``None``.

    Args:
        type_hint: A type hint, potentially ``Annotated[T, ...]``.

    Returns:
        The first marker found in metadata, or ``None`` if the hint is not
        ``Annotated`` or contains no markers.
    """
    if get_origin(type_hint) is not Annotated:
        return None
    for meta in get_args(type_hint)[1:]:
        if _is_marker(meta):
            return meta
    return None



def get_all_bindings(cls: type) -> list[tuple[str, _BaseMarker]]:
    """Returns all ``(field_name, marker)`` pairs in declaration order.

    For each dataclass field, tries ``Annotated`` metadata first, then falls
    back to the field default.  Fields with no marker are omitted.

    Args:
        cls: A dataclass type to inspect.

    Returns:
        A list of ``(field_name, marker)`` tuples for every field that
        carries a marker, preserving the class's field declaration order.
    """
    hints = get_type_hints(cls, include_extras=True)
    bindings: list[tuple[str, _BaseMarker]] = []

    for field in dataclasses.fields(cls):
        marker = _get_annotated_marker(hints.get(field.name))
        if (
            marker is None
            and field.default is not dataclasses.MISSING
            and _is_marker(field.default)
        ):
            marker = field.default
        if marker is not None:
            bindings.append((field.name, marker))

    return bindings
