from dataclasses import dataclass

import dash
import pytest

from dash_typed_callbacks.markers import Out
from dash_typed_callbacks.projection import _extract_value, project_result


@dataclass
class SampleObj:
    name: str
    value: int


def test_extract_value_attribute_access():
    """Successfully retrieves values via attribute access."""
    obj = SampleObj(name="test", value=42)
    assert _extract_value(obj, "name") == (True, "test")
    assert _extract_value(obj, "value") == (True, 42)
    assert _extract_value(obj, ["name"]) == (True, "test")
    assert _extract_value(obj, ["value"]) == (True, 42)


def test_extract_value_item_access():
    """Falls back to item access when attribute access fails."""
    obj = {"name": "test", "count": 100}
    assert _extract_value(obj, "name") == (True, "test")
    assert _extract_value(obj, "count") == (True, 100)
    assert _extract_value(obj, ["name"]) == (True, "test")
    assert _extract_value(obj, ["count"]) == (True, 100)


def test_extract_value_attribute_priority():
    """Attribute access takes priority over item access."""

    class Both:
        name = "from_attr"

        def __getitem__(self, key):
            return "from_item" if key == "name" else (_ for _ in ()).throw(KeyError(key))

    assert _extract_value(Both(), "name") == (True, "from_attr")
    assert _extract_value(Both(), ["name"]) == (True, "from_attr")


def test_extract_value_not_found():
    """Returns (False, None) when neither attribute nor item access succeeds."""
    assert _extract_value(SampleObj("x", 1), "missing") == (False, None)
    assert _extract_value({"a": 1}, "missing") == (False, None)
    assert _extract_value(SampleObj("x", 1), ["missing"]) == (False, None)
    assert _extract_value({"a": 1}, ["missing", "also_missing"]) == (False, None)


@dataclass
class OutputSchema:
    count: int
    message: str


def test_project_result_fast_path():
    """Fast path: exact type match reads fields directly."""
    result = OutputSchema(count=42, message="hello")
    bindings = [
        ("count", Out("count-id")),
        ("message", Out("msg-id")),
    ]

    projected = project_result(result, OutputSchema, bindings, strict=False)
    assert projected == (42, "hello")


def test_project_result_projection():
    """Projection from dict and foreign objects."""
    bindings = [("count", Out("count-id")), ("message", Out("msg-id"))]

    result_dict = {"count": 100, "message": "test"}
    assert project_result(result_dict, OutputSchema, bindings, strict=False) == (100, "test")

    @dataclass
    class ApiResponse:
        count: int
        message: str
        extra: str

    result_obj = ApiResponse(count=50, message="data", extra="ignored")
    assert project_result(result_obj, OutputSchema, bindings, strict=False) == (50, "data")


def test_project_result_alias():
    """Alias resolution takes priority over field name."""
    result = {"api_count": 99, "msg_text": "aliased"}
    bindings = [
        ("count", Out("count-id", alias="api_count")),
        ("message", Out("msg-id", alias="msg_text")),
    ]

    assert project_result(result, OutputSchema, bindings, strict=False) == (99, "aliased")

    result_both = {"count": 1, "api_count": 2}
    bindings_alias = [("count", Out("count-id", alias="api_count"))]
    assert project_result(result_both, OutputSchema, bindings_alias, strict=False) == (2,)


def test_project_result_missing_field_fallbacks():
    """Missing fields use default, no_update (lenient), or raise (strict)."""
    result = {"count": 10}

    bindings_with_default = [
        ("count", Out("count-id")),
        ("message", Out("msg-id", default="default_msg")),
    ]
    assert project_result(result, OutputSchema, bindings_with_default, strict=False) == (
        10,
        "default_msg",
    )
    assert project_result(result, OutputSchema, bindings_with_default, strict=True) == (
        10,
        "default_msg",
    )

    bindings_no_default = [("count", Out("count-id")), ("message", Out("msg-id"))]
    assert project_result(result, OutputSchema, bindings_no_default, strict=False) == (
        10,
        dash.no_update,
    )

    with pytest.raises(AttributeError, match="Field 'message' not found"):
        project_result(result, OutputSchema, bindings_no_default, strict=True)
