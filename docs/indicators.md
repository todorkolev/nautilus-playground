# Technical Indicators

This document describes the technical indicators available in the Nautilus Playground project.

## Available Indicators

- `pandas_ta_indicator.py`: A wrapper for the pandas-ta library that provides access to numerous technical indicators

## PandasTaIndicator

The PandasTaIndicator is a wrapper for the [pandas-ta](https://github.com/twopirllc/pandas-ta) library that allows using any indicator from the library in Nautilus Trader. This provides access to over 130 technical indicators without having to implement them individually.

### Supported Indicators

The PandasTaIndicator supports all indicators available in pandas-ta, including:

- **Trend Indicators**: ADX, MACD, Moving Averages (SMA, EMA, WMA, etc.)
- **Momentum Indicators**: RSI, Stochastic, CCI, ROC
- **Volatility Indicators**: Bollinger Bands, ATR, Keltner Channels
- **Volume Indicators**: OBV, Volume Profile, MFI
- **And many more**

For a complete list of supported indicators, see the [pandas-ta documentation](https://github.com/twopirllc/pandas-ta).

### Usage

```python
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.identifiers import InstrumentId
from src.indicators.pandas_ta_indicator import PandasTaIndicator

# Create the bar type
bar_type = BarType(
    instrument_id=InstrumentId("BTCUSDT.BINANCE"),
    bar_spec=1,
    aggregation=BarAggregation.HOUR,
    price_type=PriceType.LAST,
)

# Create an RSI indicator
rsi = PandasTaIndicator(
    bar_type=bar_type,
    indicator_name="rsi",
    params={"length": 14},
    price_type=PriceType.LAST,
)

# Create an ADX indicator
adx = PandasTaIndicator(
    bar_type=bar_type,
    indicator_name="adx",
    params={"length": 14},
    price_type=PriceType.LAST,
)

# Create a MACD indicator
macd = PandasTaIndicator(
    bar_type=bar_type,
    indicator_name="macd",
    params={"fast": 12, "slow": 26, "signal": 9},
    price_type=PriceType.LAST,
)

# Create a Bollinger Bands indicator
bbands = PandasTaIndicator(
    bar_type=bar_type,
    indicator_name="bbands",
    params={"length": 20, "std": 2},
    price_type=PriceType.LAST,
)

# In a strategy, register the indicators
self.register_indicator_for_bars(bar_type, rsi)
self.register_indicator_for_bars(bar_type, adx)
self.register_indicator_for_bars(bar_type, macd)
self.register_indicator_for_bars(bar_type, bbands)

# Access the indicator values
rsi_value = rsi.value
adx_value = adx.value
macd_value = macd.value  # Returns a dictionary with 'MACD', 'MACD_signal', and 'MACD_hist'
bbands_value = bbands.value  # Returns a dictionary with 'BBL', 'BBM', and 'BBU'
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
