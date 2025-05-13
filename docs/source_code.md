# Source Code

This document provides an overview of the source code structure for the Nautilus Playground project.

## Directory Structure

- `execution/`: Sample execution algorithms (e.g., TWAP)
- `indicators/`: Sample indicator implementations (e.g., PandasTaIndicator)
- `strategies/`: Sample strategy implementations
  - `mean_reversion/`: Mean reversion strategy with ADX filtering and ML
    - `config.yaml`: Configuration for the mean reversion strategy
    - `ml_model.py`: Machine learning models for the strategy
    - `strategy.py`: Main strategy implementation
  - `moving_average_crossover/`: Moving average crossover strategy
    - `config.yaml`: Configuration for the moving average crossover strategy
    - `strategy.py`: Main strategy implementation
  - `position_management.py`: Position management utilities
- `main_live.py`: Entry point for live trading
- `main_backtest.py`: Entry point for backtesting

## Entry Points

### Live Trading

The `main_live.py` script provides a flexible entry point for live trading with Binance. It supports:

- Loading configuration from environment variables (via `.env` file)
- Loading configuration from a YAML file
- Paper trading mode using the Binance testnet
- Customizable logging levels

Basic usage:

```bash
python src/main_live.py
```

For paper trading (using Binance testnet):

```bash
python src/main_live.py --paper
```

With a custom configuration file (if needed):

```bash
python src/main_live.py --config path/to/config.yaml
```

For detailed setup instructions, see the [Live Trading Guide](live_trading.md).

### Backtesting

To run a backtest:

```bash
python src/main_backtest.py --config path/to/config.yaml
```

You can also specify start and end dates:

```bash
python src/main_backtest.py --config path/to/config.yaml --start-date 2023-01-01 --end-date 2023-12-31
```



## Developing New Components

### Execution Algorithms

The project includes the following execution algorithms:

1. **TWAP (Time-Weighted Average Price)**
   - Located in `src/execution/twap.py`
   - Executes orders over a specified time period to achieve a price close to the time-weighted average price
   - Helps minimize market impact for large orders

Create new execution algorithms in the `execution/` directory. Inherit from `ExecutionAlgorithm` and implement the required methods.

For more information, see the [Execution Algorithms](execution_algorithms.md) documentation.

### Indicators

The project includes the following indicators:

1. **PandasTaIndicator**
   - Located in `src/indicators/pandas_ta_indicator.py`
   - A wrapper for the pandas-ta library that allows using any indicator from the library in Nautilus Trader
   - Supports all indicators available in pandas-ta, including:
     - ADX (Average Directional Index)
     - RSI (Relative Strength Index)
     - MACD (Moving Average Convergence Divergence)
     - Bollinger Bands
     - ATR (Average True Range)
     - And many more

Create new indicators in the `indicators/` directory. Inherit from `Indicator` and implement the required methods.

For more information, see the [Indicators](indicators.md) documentation and specific indicator documentation:
- [ADX Indicator](indicators/adx.md)

### Strategies

The project includes the following strategies:

1. **Moving Average Crossover Strategy**
   - Located in `src/strategies/moving_average_crossover/`
   - Generates buy signals when the fast EMA crosses above the slow EMA
   - Generates sell signals when the fast EMA crosses below the slow EMA

2. **Mean Reversion Strategy**
   - Located in `src/strategies/mean_reversion/`
   - Uses ADX as a trend filter to determine market conditions
   - Applies mean reversion techniques in range-bound markets
   - Applies trend following techniques in trending markets
   - Uses machine learning to enhance entry and exit decisions

Create new strategies in the `strategies/` directory. Inherit from `Strategy` and implement the required methods.

For more information, see the [Strategies](strategies.md) documentation and the specific strategy documentation:
- [Mean Reversion Strategy](strategies/mean_reversion.md)

### Notebooks

The project includes Jupyter notebooks in the `notebooks/` directory to explore and demonstrate strategies:

- `moving_average_crossover_backtest.ipynb`: Demonstrates backtesting and optimizing the Moving Average Crossover strategy
- `mean_reversion_strategy_exploration.ipynb`: Explores and demonstrates the Mean Reversion strategy with ADX filtering

Create new notebooks in the `notebooks/` directory to explore and demonstrate your strategies.

For more information, see the [Notebooks](notebooks.md) documentation.
