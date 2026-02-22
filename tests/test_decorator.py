from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import dash
import pytest

from dash_typed_callbacks.decorator import (
    _build_dash_dependencies,
    _build_wrapper,
    _infer_param_types,
    _register_callback,
    _resolve_return_type,
    typed_app_callback,
)
from dash_typed_callbacks.extraction import get_all_bindings
from dash_typed_callbacks.markers import In, Out, St


@dataclass
class OutputModel:
    count: int = Out("count-id")
    message: str = Out("msg-id", "children")


@dataclass
class InputModel:
    btn: int = In("btn-id", "n_clicks")
    value: str = In("input-id")


@dataclass
class StateModel:
    setting: str = St("setting-id")


OUTPUT_BINDINGS = get_all_bindings(OutputModel)


@pytest.mark.parametrize(
    "model_cls, dash_type, expected_ids",
    [
        pytest.param(OutputModel, dash.Output, ["count-id", "msg-id"], id="outputs"),
        pytest.param(InputModel, dash.Input, ["btn-id", "input-id"], id="inputs"),
        pytest.param(StateModel, dash.State, ["setting-id"], id="states"),
    ],
)
def test_build_dash_dependencies(model_cls, dash_type, expected_ids):
    """Converts markers to the corresponding Dash dependency objects."""
    deps = _build_dash_dependencies(model_cls)
    assert all(isinstance(d, dash_type) for d in deps)
    assert [d.component_id for d in deps] == expected_ids


def test_build_dash_dependencies_errors():
    """Raises TypeError for mixed marker types or models with no bindings."""

    @dataclass
    class Mixed:
        output: int = Out("out-id")
        input: int = In("in-id")

    with pytest.raises(TypeError, match="All markers.*must be the same type"):
        _build_dash_dependencies(Mixed)

    @dataclass
    class Empty:
        value: int

    with pytest.raises(TypeError, match="Empty has no marker bindings"):
        _build_dash_dependencies(Empty)


def test_resolve_return_type():
    """Extracts dataclass return type; errors on missing annotation or non-dataclass."""

    def valid_cb() -> OutputModel: ...

    assert _resolve_return_type(valid_cb) is OutputModel

    no_annotation = lambda: None
    with pytest.raises(TypeError, match="must have a return type annotation"):
        _resolve_return_type(no_annotation)

    non_dataclass = lambda: None
    non_dataclass.__annotations__["return"] = str
    with pytest.raises(TypeError, match="must be a dataclass"):
        _resolve_return_type(non_dataclass)


def test_build_wrapper():
    """Packs positional args into typed models and projects output; tuples pass through."""

    # Inputs only
    def cb_inputs(inputs: InputModel) -> OutputModel:
        return OutputModel(count=inputs.btn, message=inputs.value)

    wrapper = _build_wrapper(cb_inputs, InputModel, None, OUTPUT_BINDINGS, OutputModel, False)
    assert wrapper(5, "hello") == (5, "hello")

    # Inputs + states: splits positional args between models
    def cb_both(inputs: InputModel, states: StateModel) -> OutputModel:
        return OutputModel(count=inputs.btn, message=states.setting)

    wrapper = _build_wrapper(cb_both, InputModel, StateModel, OUTPUT_BINDINGS, OutputModel, False)
    assert wrapper(3, "text", "my-setting") == (3, "my-setting")

    # Tuple passthrough: raw tuples skip projection
    def cb_tuple(inputs: InputModel) -> OutputModel:
        return (42, "raw")  # type: ignore[return-value]

    wrapper = _build_wrapper(cb_tuple, InputModel, None, OUTPUT_BINDINGS, OutputModel, False)
    assert wrapper(1, "x") == (42, "raw")


def test_register_callback():
    """Wires correct Dash deps and wrapper; returns the original function unchanged."""
    registered: dict[str, Any] = {}

    def fake_callback(*deps, **kwargs):
        registered["deps"] = deps
        registered["kwargs"] = kwargs

        def registrar(wrapper):
            registered["wrapper"] = wrapper

        return registrar

    @_register_callback(fake_callback, InputModel, StateModel, False, {})
    def my_callback(inputs: InputModel, states: StateModel) -> OutputModel:
        return OutputModel(count=inputs.btn, message=states.setting)

    # Correct dependency types and count
    deps = registered["deps"]
    assert len(deps) == 5
    assert isinstance(deps[0], dash.Output)
    assert isinstance(deps[2], dash.Input)
    assert isinstance(deps[4], dash.State)

    # Wrapper is functional
    assert registered["wrapper"](7, "txt", "cfg") == (7, "cfg")

    # Original function returned unchanged, callable without Dash
    assert my_callback.__name__ == "my_callback"
    result = my_callback(InputModel(btn=1, value="x"), StateModel(setting="s"))
    assert isinstance(result, OutputModel)


def test_infer_param_types():
    """Infers input/state types from parameter annotations, skipping non-marker params."""

    def cb_both(inputs: InputModel, states: StateModel) -> OutputModel: ...

    assert _infer_param_types(cb_both) == (InputModel, StateModel)

    def cb_inputs_only(inputs: InputModel) -> OutputModel: ...

    assert _infer_param_types(cb_inputs_only) == (InputModel, None)

    def cb_with_extras(inputs: InputModel, x: int, name: str) -> OutputModel: ...

    assert _infer_param_types(cb_with_extras) == (InputModel, None)


@pytest.mark.parametrize(
    "extra_kwargs",
    [
        pytest.param(
            {"input_type": InputModel, "state_type": StateModel}, id="explicit_types"
        ),
        pytest.param({}, id="inferred_types"),
    ],
)
def test_typed_app_callback_with_mock(extra_kwargs):
    """Registers callback with correct deps and working wrapper, explicit or inferred."""
    mock_app = MagicMock()
    registered_wrapper = None

    def capture_wrapper(wrapper: Any) -> None:
        nonlocal registered_wrapper
        registered_wrapper = wrapper

    mock_app.callback.return_value = capture_wrapper

    @typed_app_callback(mock_app, **extra_kwargs)
    def my_callback(inputs: InputModel, states: StateModel) -> OutputModel:
        return OutputModel(count=inputs.btn, message=states.setting)

    mock_app.callback.assert_called_once()
    assert registered_wrapper is not None
    assert registered_wrapper(10, "val", "cfg") == (10, "cfg")

    # Original function returned, callable without Dash
    result = my_callback(InputModel(btn=5, value="x"), StateModel(setting="s"))
    assert result == OutputModel(count=5, message="s")


@pytest.mark.dash_integration
def test_typed_app_callback_with_real_dash_app():
    """End-to-end decorator test using a real Dash app instance."""
    import json

    app = dash.Dash(__name__)

    @typed_app_callback(app, InputModel)
    def my_callback(inputs: InputModel) -> OutputModel:
        return OutputModel(count=inputs.btn, message=inputs.value)

    assert len(app.callback_map) == 1

    # Invoke through Dash's internal dispatch mechanism
    callback_id = next(iter(app.callback_map))
    cb_entry = app.callback_map[callback_id]
    wrapper = cb_entry["callback"]
    outputs_list = [
        {"id": "count-id", "property": "value"},
        {"id": "msg-id", "property": "children"},
    ]

    raw = wrapper(42, "hello", outputs_list=outputs_list)
    result = json.loads(raw)

    assert result["response"]["count-id"]["value"] == 42
    assert result["response"]["msg-id"]["children"] == "hello"
