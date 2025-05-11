# Indicator Comparison Strategy

This strategy demonstrates the use of technical indicators from two different libraries:
- **pandas-ta**: A Python library with over 130 technical indicators
- **ta-lib**: A widely used technical analysis library

## Indicators Implemented

### pandas-ta Indicators
- `PandasTaRSI`: Relative Strength Index implementation using pandas-ta
- `PandasTaMovingAverage`: Moving Average implementation using pandas-ta (supports SMA, EMA, WMA)

### ta-lib Indicators
- `TalibRSI`: Relative Strength Index implementation using TA-Lib
- `TalibMovingAverage`: Moving Average implementation using TA-Lib (supports various MA types)

## Strategy Logic

The strategy uses both sets of indicators to:
1. Calculate RSI and Moving Averages using both libraries
2. Compare the results to show the differences (if any) between implementations
3. Generate trading signals based on:
   - Moving Average crossovers
   - RSI overbought/oversold conditions

## Configuration

The strategy can be configured via the `config.yaml` file:

```yaml
strategy:
  name: IndicatorComparisonStrategy
  config:
    instrument_id: BTCUSDT.BINANCE
    bar_type: BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL
    rsi_period: 14
    rsi_oversold: 30
    rsi_overbought: 70
    fast_ma_period: 10
    slow_ma_period: 20
    trade_size: 0.01
```

## Running the Backtest

To run the backtest:

```bash
python src/strategies/indicator_comparison/backtest.py
```

This will:
1. Load the configuration from `config.yaml`
2. Set up a backtest environment with synthetic price data
3. Run the strategy and generate performance metrics
4. Create an equity curve plot (if matplotlib is available)

## Notes

- The strategy logs the values from both indicator implementations to show any differences
- For trading decisions, the strategy uses the ta-lib indicators
- In a real-world scenario, you would typically choose one library based on your requirements
