from dataclasses import dataclass

import dash
import pytest

from dash_typed_callbacks.decorator import _build_dash_dependencies, _resolve_return_type
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


def test_build_dash_dependencies_outputs():
    """Converts Out markers to dash.Output objects."""
    deps = _build_dash_dependencies(OutputModel)

    assert len(deps) == 2
    assert isinstance(deps[0], dash.Output)
    assert deps[0].component_id == "count-id"
    assert deps[0].component_property == "value"
    assert isinstance(deps[1], dash.Output)
    assert deps[1].component_id == "msg-id"
    assert deps[1].component_property == "children"


def test_build_dash_dependencies_inputs():
    """Converts In markers to dash.Input objects."""
    deps = _build_dash_dependencies(InputModel)

    assert len(deps) == 2
    assert isinstance(deps[0], dash.Input)
    assert deps[0].component_id == "btn-id"
    assert deps[0].component_property == "n_clicks"


def test_build_dash_dependencies_states():
    """Converts St markers to dash.State objects."""
    deps = _build_dash_dependencies(StateModel)

    assert len(deps) == 1
    assert isinstance(deps[0], dash.State)
    assert deps[0].component_id == "setting-id"
    assert deps[0].component_property == "value"


def test_build_dash_dependencies_mixed_markers():
    """Raises TypeError when markers of different types are mixed."""

    @dataclass
    class Mixed:
        output: int = Out("out-id")
        input: int = In("in-id")

    with pytest.raises(TypeError, match="All markers.*must be the same type"):
        _build_dash_dependencies(Mixed)


def test_build_dash_dependencies_no_bindings():
    """Raises TypeError when model has no marker bindings."""

    @dataclass
    class Empty:
        value: int

    with pytest.raises(TypeError, match="Empty has no marker bindings"):
        _build_dash_dependencies(Empty)


def test_resolve_return_type_valid():
    """Extracts return type from a function annotated with a dataclass."""

    def my_callback() -> OutputModel:
        ...

    assert _resolve_return_type(my_callback) is OutputModel


@pytest.mark.parametrize(
    "func, match",
    [
        pytest.param(
            lambda: None,
            "must have a return type annotation",
            id="no_annotation",
        ),
        pytest.param(
            lambda: None,
            "must be a dataclass",
            id="non_dataclass",
        ),
    ],
)
def test_resolve_return_type_errors(func, match):
    """Raises TypeError for missing annotation or non-dataclass return type."""
    if match == "must be a dataclass":
        func.__annotations__["return"] = str
    with pytest.raises(TypeError, match=match):
        _resolve_return_type(func)
