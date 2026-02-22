"""Typed decorator layer that bridges user-facing dataclass models and Dash callbacks.

``typed_app_callback`` (or ``typed_callback``) takes a function whose parameters
and return type are annotated with dataclasses carrying ``Out``/``In``/``St``
markers. Input and state model types are inferred from the function's parameter
annotations, or can be provided explicitly. It translates those markers into
standard Dash dependency objects (``dash.Output``, ``dash.Input``, ``dash.State``)
and registers a callback with the Dash app.

The function registered with Dash is not the decorated function itself, but a
wrapper around it. On the inbound side, the wrapper receives Dash's flat
positional arguments and packs them into the typed input/state dataclass
instances the decorated function expects. On the outbound side, it takes
whatever the decorated function returns and projects it back into the
positional tuple that Dash requires.

The decorated function is returned unchanged, so it can still be called
directly in tests without Dash involved.
"""

import dataclasses
from collections.abc import Callable
from typing import Any, cast, get_type_hints

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


def _infer_param_types(
    func: Callable[..., Any],
) -> tuple[type | None, type | None]:
    """Infers input and state model types from a function's parameter annotations.

    Inspects each parameter's type hint, checks whether it's a dataclass with
    ``In`` or ``St`` markers, and returns the corresponding types. Parameters
    without markers or without dataclass annotations are ignored.

    Args:
        func: The callback function to inspect.

    Returns:
        A tuple of ``(input_type, state_type)``, either of which may be ``None``
        if no matching parameter was found.
    """
    hints = get_type_hints(func)
    input_type: type | None = None
    state_type: type | None = None

    for name, hint in hints.items():
        if name == "return":
            continue
        if not (dataclasses.is_dataclass(hint) and isinstance(hint, type)):
            continue

        bindings = get_all_bindings(hint)
        if not bindings:
            continue

        first_marker_type = type(bindings[0][1])
        if first_marker_type is In:
            input_type = hint
        elif first_marker_type is St:
            state_type = hint

    return input_type, state_type


def _build_wrapper(
    func: Callable[..., Any],
    input_type: type | None,
    state_type: type | None,
    output_bindings: list[tuple[str, Out]],
    return_type: type,
    strict_return: bool,
) -> Callable[..., tuple]:
    """Wraps a typed callback to translate between Dash's positional args and typed models.

    Args:
        func: The user's callback function.
        input_type: Dataclass type for inputs, or ``None`` for raw positional args.
        state_type: Dataclass type for states, or ``None`` for no states.
        output_bindings: List of ``(field_name, Out)`` pairs from the output model.
        return_type: The output dataclass type for projection.
        strict_return: Whether to raise on missing output fields.

    Returns:
        A wrapper function that Dash can call with positional args.
    """
    from dash_typed_callbacks.projection import project_result

    # Pre-compute field counts so we know how to slice Dash's flat arg list
    n_inputs = len(dataclasses.fields(input_type)) if input_type else 0
    n_states = len(dataclasses.fields(state_type)) if state_type else 0

    def wrapper(*args: Any) -> tuple:
        # Inbound: split Dash's flat positional args into typed model instances
        call_args: list[Any] = []

        if input_type is not None:
            call_args.append(input_type(*args[:n_inputs]))
        if state_type is not None:
            call_args.append(state_type(*args[n_inputs : n_inputs + n_states]))

        # No typed models — pass raw positional args through unchanged
        if not call_args:
            call_args = list(args)

        result = func(*call_args)

        # Outbound: raw tuples pass through, everything else gets projected
        # onto the output schema
        if isinstance(result, tuple):
            return result

        return project_result(result, return_type, output_bindings, strict_return)

    return wrapper


def _register_callback(
    callback_fn: Callable[..., Any],
    input_type: type | None,
    state_type: type | None,
    strict_return: bool,
    extra_kwargs: dict[str, Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Shared implementation for ``typed_callback`` and ``typed_app_callback``.

    Args:
        callback_fn: A Dash registration function (``dash.callback`` or ``app.callback``).
            Called as ``callback_fn(*deps, **kwargs)`` which returns a registrar;
            that registrar is then called with the wrapper function.
        input_type: Dataclass type for inputs, or ``None``.
        state_type: Dataclass type for states, or ``None``.
        strict_return: Whether to raise on missing output fields during projection.
        extra_kwargs: Additional keyword arguments forwarded to ``callback_fn``.

    Returns:
        A decorator that registers the callback with Dash and returns the
        original function unchanged.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return_type = _resolve_return_type(func)
        output_bindings = cast(list[tuple[str, Out]], get_all_bindings(return_type))

        # Use explicitly provided types, or infer from parameter annotations
        resolved_input = input_type
        resolved_state = state_type
        if resolved_input is None and resolved_state is None:
            resolved_input, resolved_state = _infer_param_types(func)

        output_deps = _build_dash_dependencies(return_type)
        input_deps = _build_dash_dependencies(resolved_input) if resolved_input else []
        state_deps = _build_dash_dependencies(resolved_state) if resolved_state else []

        wrapper = _build_wrapper(
            func, resolved_input, resolved_state, output_bindings, return_type, strict_return
        )

        # Programmatic equivalent of @app.callback(*deps, **kwargs) def fn(): ...
        callback_fn(
            *output_deps, *input_deps, *state_deps, **extra_kwargs
        )(wrapper)

        return func

    return decorator


def typed_callback(
    input_type: type | None = None,
    state_type: type | None = None,
    *,
    prevent_initial_call: bool = False,
    strict_return: bool = False,
    **extra_kwargs: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Registers a typed callback using the module-level ``dash.callback``.

    Args:
        input_type: Dataclass type for inputs, or ``None``.
        state_type: Dataclass type for states, or ``None``.
        prevent_initial_call: Whether to suppress the initial callback invocation.
        strict_return: Whether to raise on missing output fields during projection.
        **extra_kwargs: Additional keyword arguments forwarded to ``dash.callback``.

    Returns:
        A decorator that registers the callback with Dash.
    """
    extra_kwargs["prevent_initial_call"] = prevent_initial_call
    return _register_callback(
        dash.callback, input_type, state_type, strict_return, extra_kwargs
    )


def typed_app_callback(
    app: dash.Dash,
    input_type: type | None = None,
    state_type: type | None = None,
    *,
    prevent_initial_call: bool = False,
    strict_return: bool = False,
    **extra_kwargs: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Registers a typed callback using ``app.callback`` on a specific Dash instance.

    Args:
        app: The Dash application instance.
        input_type: Dataclass type for inputs, or ``None``.
        state_type: Dataclass type for states, or ``None``.
        prevent_initial_call: Whether to suppress the initial callback invocation.
        strict_return: Whether to raise on missing output fields during projection.
        **extra_kwargs: Additional keyword arguments forwarded to ``app.callback``.

    Returns:
        A decorator that registers the callback with the given app.
    """
    extra_kwargs["prevent_initial_call"] = prevent_initial_call
    return _register_callback(
        app.callback, input_type, state_type, strict_return, extra_kwargs
    )
