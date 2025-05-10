# Technical Indicators

This document describes the technical indicators available in the Nautilus Playground project.

## Available Indicators

- `adaptive_moving_average.py`: Adaptive Moving Average (AMA) indicator
- `relative_strength_index.py`: Relative Strength Index (RSI) indicator

## Adaptive Moving Average (AMA)

The AMA adjusts its smoothing factor based on market volatility, making it more responsive to price changes in trending markets and less responsive in ranging markets.

### Usage

```python
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.identifiers import InstrumentId
from src.indicators.adaptive_moving_average import AdaptiveMovingAverage

# Create the bar type
bar_type = BarType(
    instrument_id=InstrumentId("BTCUSDT.BINANCE"),
    bar_spec=1,
    aggregation=BarAggregation.HOUR,
    price_type=PriceType.LAST,
)

# Create the indicator
ama = AdaptiveMovingAverage(
    bar_type=bar_type,
    period=14,
    fast_period=2,
    slow_period=30,
    price_type=PriceType.LAST,
)

# In a strategy, register the indicator
self.register_indicator(ama)

# Access the indicator value
value = ama.value
```

## Relative Strength Index (RSI)

The RSI is a momentum oscillator that measures the speed and change of price movements. It oscillates between 0 and 100 and is typically used to identify overbought or oversold conditions.

### Usage

```python
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.identifiers import InstrumentId
from src.indicators.relative_strength_index import RelativeStrengthIndex

# Create the bar type
bar_type = BarType(
    instrument_id=InstrumentId("BTCUSDT.BINANCE"),
    bar_spec=1,
    aggregation=BarAggregation.HOUR,
    price_type=PriceType.LAST,
)

# Create the indicator
rsi = RelativeStrengthIndex(
    bar_type=bar_type,
    period=14,
    price_type=PriceType.LAST,
)

# In a strategy, register the indicator
self.register_indicator(rsi)

# Access the indicator value
value = rsi.value
```

## Creating New Indicators

To create a new indicator:

1. Create a new Python file in the `src/indicators/` directory
2. Inherit from `Indicator`
3. Implement the required methods:
   - `handle_bar`
   - `value` property
   - `has_inputs` property
   - `reset`

Example:

```python
from nautilus_trader.indicators.base.indicator import Indicator

class MyIndicator(Indicator):
    def __init__(self, bar_type, period, price_type=PriceType.LAST):
        super().__init__(bar_type)
        self.period = period
        self.price_type = price_type
        # Initialize your indicator
        
    def handle_bar(self, bar):
        # Update the indicator with the given bar
        
    @property
    def value(self):
        # Return the current indicator value
        
    @property
    def has_inputs(self):
        # Return whether the indicator has inputs
        
    def reset(self):
        # Reset the indicator
```
