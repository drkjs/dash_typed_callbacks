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

@typed_app_callback(app, Inputs, States)
def calculate(inputs: Inputs, states: States) -> Outputs:
    subtotal = states.price * states.quantity
    tax = subtotal * 0.1
    return Outputs(
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax
    )
```

## Planned Features

- **Named fields** — return objects with clear, documented attributes
- **Flexible syntax** — use `Annotated[T, Out(...)]` or `field: T = Out(...)`, mix freely
- **Automatic projection** — return any object (dataclass, dict, Pydantic model) and it auto-maps to your outputs - helpful if you have an API call that returns a Pydantic model and you just want to return (a subset of) the returned data

## Status
The code is under active development.
