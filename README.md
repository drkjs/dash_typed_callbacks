## dash_typed_callbacks

Type-safe, readable Dash callbacks with named fields instead of messy return values. 

If your Dash UI gets a little more involved, you might find yourself returning quite the number of arguments from your callbacks. Or its the other way around: your callback depends on numerous inputs. In such situations, Dash callbacks can become unreadable: 

```python
@app.callback(
    Output("subtotal", "value"),
    Output("tax", "value"),
    Output("total", "value"),
    # ... 12 more outputs
    Input("calc-btn", "n_clicks"),
    State("price", "value"),
    State("qty", "value"),
)
def calculate(n_clicks, price, qty):
    return sub, tax, total  # Hope THIS order matches the decorator...
```

While [flexible callback signatures](https://dash.plotly.com/flexible-callback-signatures) are a thing, this can still be quite messy sometime. So instead, the solution proposed here is that instead, we should use typed dataclasses with named fields for in- as well as outputs: 

```python
from dataclasses import dataclass
from typing import Annotated
from dash_typed_callbacks import Out, In, St, typed_app_callback

@dataclass
class Inputs:
    clicks: Annotated[int, In("button", "n_clicks")]

@dataclass
class States:
    price: Annotated[float, St("price-input", "value")]
    quantity: Annotated[int, St("qty-input", "value")]

@dataclass
class Outputs:
    subtotal: Annotated[float, Out("subtotal", "value")]
    tax: Annotated[float, Out("tax", "value")]
    total: Annotated[float, Out("total", "value")]

@typed_app_callback(app)
def calculate(inputs: Inputs, states: States) -> Outputs:
    subtotal = states.price * states.quantity
    tax = subtotal * 0.1
    return Outputs(
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax
    )
```

Input and state types are inferred from the function's parameter annotations. You can also pass them explicitly if you prefer:

```python
@typed_app_callback(app, Inputs, States)
def calculate(inputs: Inputs, states: States) -> Outputs:
    ...
```

### `@DashModel` decorator

Instead of `@dataclass`, you can use `@DashModel` to get a few utility methods for free:

```python
from dash_typed_callbacks import DashModel, Out

@DashModel
class Outputs:
    subtotal: float = Out("subtotal", "value")
    tax: float = Out("tax", "value")
    total: float = Out("total", "value")

Outputs.field_names()   # ['subtotal', 'tax', 'total']
Outputs.dash_fields()   # [('subtotal', Out(...)), ('tax', Out(...)), ...]

result = Outputs(subtotal=90.0, tax=9.0, total=99.0)
result.to_tuple()       # (90.0, 9.0, 99.0)
```

This is entirely optional — plain `@dataclass` classes work with `typed_app_callback` just as well. `@DashModel` can also be stacked on top of an existing `@dataclass` decorator (e.g. `@dataclass(frozen=True)`) without double-wrapping.

## Features

- **Named fields** — return objects with clear, documented attributes instead of positional tuples
- **Flexible syntax** — use `Annotated[T, Out(...)]` or `field: T = Out(...)`, mix freely
- **Type inference** — input and state types are inferred from function annotations, or can be passed explicitly
- **Automatic projection** — return any object (dataclass, dict, Pydantic model) and it auto-maps to your outputs
- **`@DashModel` decorator** — optional drop-in replacement for `@dataclass` that adds `to_tuple()`, `dash_fields()`, and `field_names()` utilities

## Status

The code is under active development.
