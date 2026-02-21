import dataclasses
from collections.abc import Callable
from typing import Any, get_type_hints

import dash

from dash_typed_callbacks.extraction import get_all_bindings
from dash_typed_callbacks.markers import In, Out, St

_MARKER_TO_DASH: dict[type, type] = {
    Out: dash.Output,
    In: dash.Input,
    St: dash.State,
}


def _build_dash_dependencies(
    model_cls: type,
) -> list[dash.Output | dash.Input | dash.State]:
    """Builds Dash dependency objects from a model's marker bindings.

    Args:
        model_cls: A dataclass with marker bindings.

    Returns:
        A list of Dash Output/Input/State objects.

    Raises:
        TypeError: If the model has no marker bindings, or if markers of
            different types are mixed in the same model.
    """
    bindings = get_all_bindings(model_cls)

    if not bindings:
        raise TypeError(f"{model_cls.__name__} has no marker bindings")

    first_field, first_marker = bindings[0]
    expected_type = type(first_marker)

    dash_deps = []
    for field_name, marker in bindings:
        if type(marker) is not expected_type:
            raise TypeError(
                f"Field {field_name!r} has {type(marker).__name__} marker, "
                f"but {first_field!r} has {expected_type.__name__}. "
                f"All markers in {model_cls.__name__} must be the same type"
            )

        dash_type = _MARKER_TO_DASH[type(marker)]
        dash_deps.append(dash_type(marker.component_id, marker.prop))

    return dash_deps


def _resolve_return_type(func: Callable[..., Any]) -> type:
    """Extracts and validates the return type annotation from a callback function.

    Args:
        func: The decorated callback function.

    Returns:
        The return type, which must be a dataclass class (not an instance).

    Raises:
        TypeError: If the function has no return annotation or the return type
            is not a dataclass class.
    """
    hints = get_type_hints(func)
    if "return" not in hints:
        raise TypeError(
            f"{func.__name__} must have a return type annotation"
        )

    return_type = hints["return"]
    if not (dataclasses.is_dataclass(return_type) and isinstance(
        return_type, type
    )):
        raise TypeError(
            f"Return type of {func.__name__} must be a dataclass, "
            f"got {return_type!r}"
        )

    return return_type
