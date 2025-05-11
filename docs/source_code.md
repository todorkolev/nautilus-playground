# Source Code

This document provides an overview of the source code structure for the Nautilus Playground project.

## Directory Structure

- `execution/`: Sample execution algorithms (e.g., TWAP)
- `indicators/`: Sample indicator implementations (e.g., Adaptive Moving Average, RSI)
- `strategies/`: Sample strategy implementations (e.g., Moving Average Crossover)
- `notebooks/`: Jupyter notebooks for exploring and demonstrating strategies
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

Create new execution algorithms in the `execution/` directory. Inherit from `ExecutionAlgorithm` and implement the required methods.

For more information, see the [Execution Algorithms](execution_algorithms.md) documentation.

### Indicators

Create new indicators in the `indicators/` directory. Inherit from `Indicator` and implement the required methods.

For more information, see the [Indicators](indicators.md) documentation.

### Strategies

Create new strategies in the `strategies/` directory. Inherit from `Strategy` and implement the required methods.

For more information, see the [Strategies](strategies.md) documentation.

### Notebooks

Create new notebooks in the `notebooks/` directory to explore and demonstrate your strategies.

For more information, see the [Notebooks](notebooks.md) documentation.
