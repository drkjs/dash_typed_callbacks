from typing import Any


class _Unset:
    """Sentinel to distinguish 'no default provided' from 'default is None'."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET = _Unset()


def _normalize_id(component_id: str | dict) -> Any:
    """Makes dict component IDs hashable for use in ``__hash__``.

    Dash supports pattern-matching callback IDs as dicts, which are not
    hashable. This converts them to frozensets so markers with dict IDs
    can be stored in sets and used as dict keys.

    Args:
        component_id: A string or pattern-matching dict component ID.

    Returns:
        The original string, or a frozenset of the dict's items.
    """
    if isinstance(component_id, dict):
        return frozenset(component_id.items())
    return component_id


class _BaseMarker:
    """Base class for Out, In, and St markers.

    Provides shared ``__init__``, ``__repr__``, ``__eq__``, and ``__hash__``.
    Equality is type-strict: ``Out('a') != In('a')``. Hash includes the
    concrete type so different marker kinds don't collide in sets/dicts.
    """

    __slots__ = ("component_id", "prop", "alias")

    def __init__(
        self,
        component_id: str | dict,
        prop: str = "value",
        *,
        alias: str | None = None,
    ) -> None:
        self.component_id = component_id
        self.prop = prop
        self.alias = alias

    def __repr__(self) -> str:
        """Returns a reconstructable string like ``Out('my-id', 'value')``."""
        cls_name = type(self).__name__
        parts = [repr(self.component_id), repr(self.prop)]
        for extra in self._repr_extras():
            parts.append(extra)
        return f"{cls_name}({', '.join(parts)})"

    def _repr_extras(self) -> list[str]:
        """Override hook for subclasses to append extra repr parts.

        Returns:
            A list of formatted ``key=value`` strings to include in repr.
        """
        extras: list[str] = []
        if self.alias is not None:
            extras.append(f"alias={self.alias!r}")
        return extras

    def __eq__(self, other: object) -> bool:
        """Compares by type, component_id, and prop.

        Returns ``NotImplemented`` for different marker types so that
        ``Out('a') == In('a')`` is ``False`` rather than raising.
        """
        if type(self) is not type(other):
            return NotImplemented
        return self.component_id == other.component_id and self.prop == other.prop

    def __hash__(self) -> int:
        """Hashes by ``(type, normalized_component_id, prop)``."""
        return hash((type(self), _normalize_id(self.component_id), self.prop))


class Out(_BaseMarker):
    """Marks a field as a Dash Output binding.

    Args:
        component_id: The Dash component ID (str or pattern-matching dict).
        prop: The component property to bind to.
        alias: Alternative attribute name to look up during projection.
        default: Fallback value when projection can't find the field.
    """

    __slots__ = ("default",)

    def __init__(
        self,
        component_id: str | dict,
        prop: str = "value",
        *,
        alias: str | None = None,
        default: Any = UNSET,
    ) -> None:
        super().__init__(component_id, prop, alias=alias)
        self.default = default

    def _repr_extras(self) -> list[str]:
        """Extends base extras with ``default=`` when a default is set."""
        extras = super()._repr_extras()
        if self.default is not UNSET:
            extras.append(f"default={self.default!r}")
        return extras


class In(_BaseMarker):
    """Marks a field as a Dash Input binding.

    Args:
        component_id: The Dash component ID (str or pattern-matching dict).
        prop: The component property to bind to.
        alias: Alternative attribute name for potential future use.
    """


class St(_BaseMarker):
    """Marks a field as a Dash State binding.

    Args:
        component_id: The Dash component ID (str or pattern-matching dict).
        prop: The component property to bind to.
        alias: Alternative attribute name for potential future use.
    """


def _is_marker(obj: Any) -> bool:
    """Returns ``True`` if *obj* is an ``Out``, ``In``, or ``St`` instance.

    Args:
        obj: Any object to check.

    Returns:
        Whether the object is a marker instance.
    """
    return isinstance(obj, _BaseMarker)
