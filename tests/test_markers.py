import pytest

from dash_typed_callbacks.markers import UNSET, In, Out, St, _is_marker


def test_unset_sentinel():
    assert repr(UNSET) == "UNSET"
    assert not UNSET
    assert bool(UNSET) is False
    assert UNSET is not None


@pytest.mark.parametrize("cls", [Out, In, St])
def test_construction_shared_defaults(cls):
    marker = cls("my-id")
    assert marker.component_id == "my-id"
    assert marker.prop == "value"
    assert marker.alias is None


@pytest.mark.parametrize("cls", [Out, In, St])
def test_construction_custom_prop_and_alias(cls):
    marker = cls("my-id", "children", alias="other")
    assert marker.prop == "children"
    assert marker.alias == "other"


@pytest.mark.parametrize("cls", [Out, In, St])
def test_construction_pattern_matching_dict_id(cls):
    marker = cls({"type": "dynamic", "index": 0})
    assert marker.component_id == {"type": "dynamic", "index": 0}


def test_construction_out_default_variations():
    assert Out("x").default is UNSET
    assert Out("x", default=None).default is None
    assert Out("x", default=42).default == 42


@pytest.mark.parametrize("cls", [In, St])
def test_construction_in_st_have_no_default_attr(cls):
    with pytest.raises(AttributeError):
        cls("x").default  # noqa: B018


@pytest.mark.parametrize(
    "marker, expected",
    [
        (Out("x"), "Out('x', 'value')"),
        (In("x", "n_clicks"), "In('x', 'n_clicks')"),
        (St("x"), "St('x', 'value')"),
    ],
)
def test_repr_basic(marker, expected):
    assert repr(marker) == expected


def test_repr_out_with_extras():
    assert repr(Out("x", alias="y")) == "Out('x', 'value', alias='y')"
    assert repr(Out("x", default=0)) == "Out('x', 'value', default=0)"
    assert (
        repr(Out("x", alias="y", default=0))
        == "Out('x', 'value', alias='y', default=0)"
    )


def test_repr_in_with_alias():
    assert repr(In("x", alias="y")) == "In('x', 'value', alias='y')"


@pytest.mark.parametrize("cls", [Out, In, St])
def test_equality_same_type_id_prop(cls):
    assert cls("a", "prop") == cls("a", "prop")


def test_equality_not_equal_different_id_or_prop():
    assert Out("a") != Out("b")
    assert Out("a", "value") != Out("a", "children")


def test_equality_cross_type_and_non_marker():
    assert Out("a") != In("a")
    assert Out("a") != St("a")
    assert In("a") != St("a")
    assert Out("a") != "not a marker"


def test_equality_alias_and_default_ignored():
    assert Out("a", alias="x") == Out("a", alias="y")
    assert Out("a", default=0) == Out("a", default=99)


def test_equality_pattern_matching_ids():
    id_a = {"type": "dynamic", "index": 0}
    assert Out(id_a) == Out({"type": "dynamic", "index": 0})
    assert Out(id_a) != Out({"type": "dynamic", "index": 1})


def test_hash_consistent_with_equality():
    assert hash(Out("a")) == hash(Out("a"))
    assert hash(In("a", "clicks")) == hash(In("a", "clicks"))
    assert hash(Out("a")) != hash(In("a"))


def test_hash_usable_in_set_and_dict():
    s = {Out("a"), Out("a"), In("a")}
    assert len(s) == 2

    d = {Out("a"): 1, In("a"): 2}
    assert d[Out("a")] == 1
    assert d[In("a")] == 2


def test_hash_pattern_matching_id():
    pid = {"type": "x", "index": 0}
    assert hash(Out(pid)) == hash(Out({"type": "x", "index": 0}))
    assert len({Out(pid), Out(pid)}) == 1


def test_is_marker():
    assert _is_marker(Out("a"))
    assert _is_marker(In("a"))
    assert _is_marker(St("a"))
    assert not _is_marker("string")
    assert not _is_marker(42)
    assert not _is_marker(None)
    assert not _is_marker(UNSET)
