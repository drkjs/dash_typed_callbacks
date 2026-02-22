import dataclasses

from dash_typed_callbacks.markers import In, Out, St
from dash_typed_callbacks.models import DashModel


@DashModel
class OutputModel:
    count: int = Out("count-id")
    message: str = Out("msg-id", "children")


@DashModel
class InputModel:
    btn: int = In("btn-id", "n_clicks")
    value: str = In("input-id")


@DashModel
class StateModel:
    setting: str = St("setting-id")


def test_dash_fields_and_field_names():
    """dash_fields() returns (name, marker) pairs; field_names() returns names."""
    fields = OutputModel.dash_fields()
    assert len(fields) == 2
    assert fields[0][0] == "count"
    assert isinstance(fields[0][1], Out)
    assert fields[1][0] == "message"

    assert InputModel.field_names() == ["btn", "value"]
    assert StateModel.field_names() == ["setting"]


def test_to_tuple():
    """to_tuple() returns marker-bound field values in declaration order."""
    model = OutputModel(count=42, message="hello")
    assert model.to_tuple() == (42, "hello")

    model = InputModel(btn=3, value="test")
    assert model.to_tuple() == (3, "test")


def test_already_a_dataclass():
    """DashModel does not double-wrap a class already decorated with @dataclass."""

    @DashModel
    @dataclasses.dataclass(frozen=True)
    class FrozenOutputs:
        value: float = Out("val-id")

    assert dataclasses.is_dataclass(FrozenOutputs)
    model = FrozenOutputs(value=3.14)
    assert model.to_tuple() == (3.14,)
    assert FrozenOutputs.field_names() == ["value"]


def test_to_tuple_skips_non_marker_fields():
    """to_tuple() only includes values for marker-bound fields."""

    @DashModel
    class MixedModel:
        output: int = Out("out-id")
        extra: str = "not a marker"

    model = MixedModel(output=10, extra="ignored")
    assert model.to_tuple() == (10,)
    assert MixedModel.field_names() == ["output"]
