from dataclasses import dataclass

import dash
import pytest

from dash_typed_callbacks.decorator import _build_dash_dependencies
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
