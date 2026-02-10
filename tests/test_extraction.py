from dataclasses import dataclass
from typing import Annotated

import pytest

from dash_typed_callbacks.extraction import get_all_bindings
from dash_typed_callbacks.markers import In, Out, St


@dataclass
class AnnotatedModel:
    x: Annotated[float, Out("x-id")]
    y: Annotated[float, In("y-id", "n_clicks")]
    z: Annotated[str, St("z-id")]


@dataclass
class DefaultModel:
    x: float = Out("x-id")
    y: float = In("y-id", "n_clicks")
    z: str = St("z-id")


@dataclass
class MixedModel:
    x: Annotated[float, Out("x-id")]
    y: float = In("y-id")


@dataclass
class AnnotatedWinsModel:
    x: Annotated[float, Out("annotated-id")] = Out("default-id")


@dataclass
class MultipleMarkersModel:
    x: Annotated[float, Out("first"), In("second")]


@dataclass
class NonMarkerExtrasModel:
    x: Annotated[float, "some string", Out("x-id"), 42]


@dataclass
class UnmarkedFieldModel:
    x: float
    y: Annotated[float, Out("y-id")]


@pytest.mark.parametrize("cls", [AnnotatedModel, DefaultModel])
def test_get_all_bindings_extracts_all_markers(cls):
    bindings = get_all_bindings(cls)
    assert len(bindings) == 3
    names, markers = zip(*bindings)
    assert list(names) == ["x", "y", "z"]
    assert isinstance(markers[0], Out)
    assert isinstance(markers[1], In)
    assert isinstance(markers[2], St)


def test_get_all_bindings_mixed():
    bindings = get_all_bindings(MixedModel)
    assert len(bindings) == 2
    assert bindings[0] == ("x", Out("x-id"))
    assert bindings[1] == ("y", In("y-id"))


def test_get_all_bindings_annotated_wins_over_default():
    bindings = get_all_bindings(AnnotatedWinsModel)
    assert len(bindings) == 1
    assert bindings[0][1].component_id == "annotated-id"


def test_get_all_bindings_multiple_markers_first_wins():
    bindings = get_all_bindings(MultipleMarkersModel)
    assert len(bindings) == 1
    assert isinstance(bindings[0][1], Out)
    assert bindings[0][1].component_id == "first"


def test_get_all_bindings_non_marker_extras_skipped():
    bindings = get_all_bindings(NonMarkerExtrasModel)
    assert len(bindings) == 1
    assert isinstance(bindings[0][1], Out)
    assert bindings[0][1].component_id == "x-id"


def test_get_all_bindings_skips_unmarked_fields():
    bindings = get_all_bindings(UnmarkedFieldModel)
    assert len(bindings) == 1
    assert bindings[0][0] == "y"


def test_get_all_bindings_preserves_declaration_order():
    @dataclass
    class OrderModel:
        c: Annotated[str, St("c-id")]
        a: Annotated[float, Out("a-id")]
        b: Annotated[float, In("b-id")]

    names = [name for name, _ in get_all_bindings(OrderModel)]
    assert names == ["c", "a", "b"]
