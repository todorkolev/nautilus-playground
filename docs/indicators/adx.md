# Average Directional Index (ADX) Indicator

This document describes the Average Directional Index (ADX) indicator implemented in this project.

## Overview

The Average Directional Index (ADX) is a technical indicator used to determine the strength of a trend, regardless of its direction. It was developed by J. Welles Wilder and introduced in his 1978 book, "New Concepts in Technical Trading Systems."

## Components

The ADX indicator consists of three components:

1. **ADX**: The main line that measures trend strength (0-100)
2. **+DI**: The positive directional indicator
3. **-DI**: The negative directional indicator

## Interpretation

- **ADX Value**: Measures the strength of a trend, regardless of direction
  - 0-25: Weak trend or no trend
  - 25-50: Strong trend
  - 50-75: Very strong trend
  - 75-100: Extremely strong trend

- **+DI and -DI**: Indicate the direction of the trend
  - +DI > -DI: Uptrend
  - -DI > +DI: Downtrend
  - Crossovers of +DI and -DI can signal potential trend changes

## Calculation

The ADX is calculated in several steps:

1. Calculate the True Range (TR):
   ```
   TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
   ```

2. Calculate the Directional Movement (DM):
   ```
   +DM = high - prev_high (if high - prev_high > prev_low - low and high - prev_high > 0, else 0)
   -DM = prev_low - low (if prev_low - low > high - prev_high and prev_low - low > 0, else 0)
   ```

3. Calculate the smoothed Average True Range (ATR):
   ```
   ATR = ((period - 1) * prev_ATR + TR) / period
   ```

4. Calculate the smoothed Directional Indicators:
   ```
   +DI = 100 * ((period - 1) * prev_+DI + +DM / ATR) / period
   -DI = 100 * ((period - 1) * prev_-DI + -DM / ATR) / period
   ```

5. Calculate the Directional Index (DX):
   ```
   DX = 100 * abs(+DI - -DI) / (+DI + -DI)
   ```

6. Calculate the Average Directional Index (ADX):
   ```
   ADX = ((period - 1) * prev_ADX + DX) / period
   ```

## Implementation

The ADX indicator is implemented in `src/indicators/adx.py`. It follows the Nautilus Trader indicator pattern and provides the following functionality:

- Initialization with a specified period (default: 14)
- Handling of bar data to update the indicator
- Properties to access the current ADX, +DI, and -DI values
- Reset functionality to clear the indicator state

### Usage

```python
from src.indicators.adx import AverageDirectionalIndex
from nautilus_trader.model.data import BarType

# Create an ADX indicator with a 14-period lookback
bar_type = BarType.from_str("BTCUSDT.BINANCE-1-HOUR-LAST-EXTERNAL")
adx = AverageDirectionalIndex(
    bar_type=bar_type,
    period=14,
)

# Register the indicator with the strategy
self.register_indicator_for_bars(bar_type, adx)

# Access the indicator values
adx_value = adx.value
plus_di = adx.positive_directional_index
minus_di = adx.negative_directional_index

# Check if the indicator is initialized
if adx.initialized:
    # Use the indicator values
    if adx_value < 25:
        print("Weak trend or no trend")
    elif adx_value < 50:
        print("Strong trend")
    elif adx_value < 75:
        print("Very strong trend")
    else:
        print("Extremely strong trend")
    
    if plus_di > minus_di:
        print("Uptrend")
    else:
        print("Downtrend")
```

## Considerations

- The ADX is a lagging indicator, meaning it confirms trends after they have started
- It does not predict future price movements, but rather measures the strength of the current trend
- It is often used in conjunction with other indicators to confirm signals
- The default period is 14, but this can be adjusted based on the timeframe and trading style
- The ADX requires OHLC data and cannot be calculated from tick data alone

## References

- Wilder, J. W. (1978). New Concepts in Technical Trading Systems.
- [Investopedia: Average Directional Index (ADX)](https://www.investopedia.com/terms/a/adx.asp)
- [StockCharts: Average Directional Index (ADX)](https://school.stockcharts.com/doku.php?id=technical_indicators:average_directional_index_adx)
