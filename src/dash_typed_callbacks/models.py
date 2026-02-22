"""Optional ``@DashModel`` decorator for typed Dash callback models.

Replaces ``@dataclass`` and adds utility methods (``to_tuple``,
``dash_fields``, ``field_names``) to the decorated class.  Entirely
optional — plain ``@dataclass`` classes work with the decorator just
as well.
"""

import dataclasses

from dash_typed_callbacks.extraction import get_all_bindings
from dash_typed_callbacks.markers import _BaseMarker


def _to_tuple(self) -> tuple:
    """Returns marker-bound field values as a tuple in declaration order."""
    return tuple(getattr(self, name) for name, _ in type(self).dash_fields())


def _dash_fields(cls) -> list[tuple[str, _BaseMarker]]:
    """Returns all ``(field_name, marker)`` pairs in declaration order."""
    return get_all_bindings(cls)


def _field_names(cls) -> list[str]:
    """Returns marker-bound field names in declaration order."""
    return [name for name, _ in cls.dash_fields()]


def DashModel(cls: type) -> type:
    """Decorator that applies ``@dataclass`` and adds Dash utility methods.

    Usage::

        @DashModel
        class MyOutputs:
            total: float = Out("total-id")
            tax: float = Out("tax-id")

        model = MyOutputs(total=100.0, tax=10.0)
        model.to_tuple()    # (100.0, 10.0)
        MyOutputs.field_names()  # ['total', 'tax']

    Args:
        cls: The class to decorate.

    Returns:
        The class, now a dataclass with ``to_tuple``, ``dash_fields``,
        and ``field_names`` methods attached.
    """
    if not dataclasses.is_dataclass(cls):
        cls = dataclasses.dataclass(cls)
    cls.to_tuple = _to_tuple  # type: ignore[attr-defined]
    cls.dash_fields = classmethod(_dash_fields)  # type: ignore[attr-defined]
    cls.field_names = classmethod(_field_names)  # type: ignore[attr-defined]
    return cls
