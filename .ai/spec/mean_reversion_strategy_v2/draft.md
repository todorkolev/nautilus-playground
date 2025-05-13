- Perform Augmented Dickey-Fuller (ADF) test to identify mean-reverting behavior
- If mean reversion is detected, create an Ornstein-Uhlenbeck (OU) model
- If the OU model confirms a mean-reverting behavior, deploy a grid trading strategy using the params from the OU process

- When price exceeds two times the standard deviation:
- Train a simple machine learning model based on multiple indicators, including statistical ones
- Use the model to predict if the trend will continue

- When the trend prediction model indicates a continuing trend, close the losing positions and open a new position to follow the trend

- Grid positions: Implement fixed take profit levels
- Trend positions: Use trailing stop loss

## Implementation Notes
- Use Nautilus Trader
- Use @main_backtest.py for backtesting
