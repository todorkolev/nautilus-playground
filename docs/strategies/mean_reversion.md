# Mean Reversion Strategy

This document describes the mean reversion strategy implemented in this project.

## Overview

The mean reversion strategy is based on the principle that prices tend to revert to their mean over time. It uses the Average Directional Index (ADX) as a trend filter to determine whether to apply mean reversion or trend following techniques.

## Strategy Components

### ADX Indicator

The Average Directional Index (ADX) is a technical indicator used to determine the strength of a trend, regardless of its direction. It consists of three components:

1. **ADX**: The main line that measures trend strength (0-100)
2. **+DI**: The positive directional indicator
3. **-DI**: The negative directional indicator

The strategy uses two ADX indicators:
- **Hourly ADX**: For short-term trend strength
- **Daily ADX**: For longer-term trend strength

### Stationarity Testing

The strategy uses the Augmented Dickey-Fuller (ADF) test to determine if the price series is stationary. A stationary series is more likely to exhibit mean-reverting behavior.

### Ornstein-Uhlenbeck Process

The Ornstein-Uhlenbeck (OU) process is a mathematical model used to describe mean-reverting behavior. The strategy estimates the parameters of the OU process to determine the mean and standard deviation of the price series.

## Strategy Logic

### Mean Reversion Mode

When the ADX indicates low trend strength (ADX < 20 for daily and < 30 for hourly), the strategy operates in mean reversion mode:

1. Check if the price series is stationary using the ADF test
2. If stationary, estimate the OU parameters to determine the mean and standard deviation
3. Calculate the distance from the current price to the mean in standard deviations
4. If the distance is within the threshold (default: 2.0 standard deviations):
   - Go LONG if the price is below the mean
   - Go SHORT if the price is above the mean
5. Use a shrinking range position management approach with take profit and stop loss levels that gradually move toward the current price over time

### Trend Following Mode

When the ADX indicates strong trend strength (ADX > 50 for hourly), the strategy switches to trend following mode:

1. Calculate the distance from the current price to the mean in standard deviations
2. If the distance is greater than twice the threshold (default: > 4.0 standard deviations):
   - Check the +DI and -DI values to determine trend direction
   - Go LONG if +DI > -DI and price is above the mean
   - Go SHORT if +DI < -DI and price is below the mean
3. Use a trailing stop position management approach with a stop loss that moves in the direction of the trend

## Position Management

The strategy uses two position management approaches:

### Shrinking Range Position

For mean reversion trades, the strategy uses a shrinking range position management approach:

1. Set initial take profit and stop loss levels based on the standard deviation
2. Hold these levels for a specified period (default: 8 hours)
3. Gradually move the levels toward the current price over a decay period (default: 48 hours)

### Trailing Stop Position

For trend following trades, the strategy uses a trailing stop position management approach:

1. Set an initial stop loss based on a percentage of the entry price (default: 0.5%)
2. Move the stop loss in the direction of the trend as the price moves favorably

## Configuration Parameters

The strategy has several configurable parameters:

- `lookback`: Number of bars to use for calculating mean and standard deviation (default: 168)
- `std_dev_threshold`: Standard deviation threshold for entry signals (default: 2.0)
- `positions_per_side`: Maximum number of positions per side (default: 3)
- `take_profit_std_dev_multiplier`: Take profit standard deviation multiplier (default: 1.0)
- `stop_loss_std_dev_multiplier`: Stop loss standard deviation multiplier (default: 2.0)
- `take_profit_hold`: Time to hold the take profit price (in minutes, default: 8 hours)
- `take_profit_decay`: Time to decay the take profit price (in minutes, default: 48 hours)
- `stop_loss_hold`: Time to hold the stop loss price (in minutes, default: 8 hours)
- `stop_loss_decay`: Time to decay the stop loss price (in minutes, default: 48 hours)
- `trailing_stop_pct`: Trailing stop percentage for trend following (default: 0.5%)

## Implementation

The strategy is implemented in the following files:

- `src/indicators/adx.py`: Implementation of the ADX indicator
- `src/strategies/mean_reversion.py`: Implementation of the mean reversion strategy
- `src/strategies/position_management.py`: Implementation of position management classes

## Running the Strategy

To run the strategy:

1. Download historical data:
   ```bash
   python scripts/download_data.py --symbols BTCUSDT --timeframes 1h 1d --days 90
   ```

2. Run the backtest:
   ```bash
   python src/main_backtest.py
   ```

3. Optionally, specify a date range:
   ```bash
   python src/main_backtest.py --start-date 2023-01-01 --end-date 2023-03-31
   ```

## Performance Considerations

- The strategy performs best in range-bound markets with low trend strength
- It can also capture trends when they are strong and persistent
- The strategy may struggle in choppy markets with frequent trend changes
- The ADX filter helps to avoid false signals in trending markets
