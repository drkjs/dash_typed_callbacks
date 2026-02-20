from collections.abc import Iterable
from contextlib import suppress
from typing import Any

import dash

from dash_typed_callbacks.markers import UNSET, Out


def _extract_value(obj: Any, keys: str | Iterable[str]) -> tuple[bool, Any]:
    """Attempts to retrieve a value from an object by attribute or item access.

    Args:
        obj: The object to extract from.
        keys: A single key or iterable of keys to try in order.

    Returns:
        A tuple of ``(found, value)`` where ``found`` is ``True`` if any key
        was successfully retrieved, ``False`` otherwise.
    """
    if isinstance(keys, str):
        keys = [keys]

    for key in keys:
        with suppress(AttributeError):
            return (True, getattr(obj, key))

        with suppress(KeyError, TypeError):
            return (True, obj[key])

    return (False, None)


def project_result(
    result: Any,
    return_type: type,
    output_bindings: list[tuple[str, Out]],
    strict: bool,
) -> tuple:
    """Projects a returned object onto the output schema, producing a tuple.

    Args:
        result: The object returned from the callback function.
        return_type: The expected return type (the output dataclass).
        output_bindings: List of ``(field_name, Out)`` pairs defining the output schema.
        strict: If ``True``, raises ``AttributeError`` when a field is missing and has
            no default. If ``False``, uses ``dash.no_update`` for missing fields.

    Returns:
        A tuple of values matching the order of ``output_bindings``.

    Raises:
        AttributeError: When ``strict=True`` and a required field is missing from ``result``.
    """
    values = []

    for field_name, out_marker in output_bindings:
        if isinstance(result, return_type):
            values.append(getattr(result, field_name))
            continue

        lookup_names = [out_marker.alias] if out_marker.alias else []
        lookup_names.append(field_name)

        found, value = _extract_value(result, lookup_names)
        if found:
            values.append(value)
            continue

        if out_marker.default is not UNSET:
            values.append(out_marker.default)
        elif strict:
            raise AttributeError(
                f"Field {field_name!r} not found on {type(result).__name__} "
                f"and has no default"
            )
        else:
            values.append(dash.no_update)

    return tuple(values)
