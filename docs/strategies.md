# Trading Strategies

This document describes the trading strategies available in the Nautilus Playground project.

## Available Strategies

- `moving_average_crossover/`: Moving Average Crossover strategy
- `mean_reversion/`: Mean Reversion strategy with ADX filtering and machine learning

## Moving Average Crossover Strategy

This strategy generates buy signals when the fast EMA crosses above the slow EMA, and sell signals when the fast EMA crosses below the slow EMA.

### Configuration

```python
from decimal import Decimal
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId
from src.strategies.moving_average_crossover import MovingAverageCrossoverConfig

# Create the bar type
bar_type = BarType(
    instrument_id=InstrumentId("BTCUSDT.BINANCE"),
    bar_spec=1,
    aggregation=BarAggregation.HOUR,
    price_type=PriceType.LAST,
)

# Create the strategy configuration
config = MovingAverageCrossoverConfig(
    instrument_id=InstrumentId("BTCUSDT.BINANCE"),
    bar_type=bar_type,
    fast_ema_period=10,
    slow_ema_period=20,
    trade_size=Decimal("0.1"),
)
```

### Usage

```python
from src.strategies.moving_average_crossover import MovingAverageCrossover

# Create the strategy
strategy = MovingAverageCrossover(config=config)

# Add to a trading engine
engine.add_strategy(strategy=strategy)
```

## Mean Reversion Strategy

This strategy combines mean reversion and trend following approaches using ADX (Average Directional Index) as a trend filter. For detailed documentation, see [Mean Reversion Strategy](strategies/mean_reversion.md).

### Configuration

```python
from decimal import Decimal
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId
from src.strategies.mean_reversion import MeanReversionStrategyConfig

# Create the bar types
hourly_bar_type = BarType(
    instrument_id=InstrumentId("BTCUSDT.BINANCE"),
    bar_spec=1,
    aggregation=BarAggregation.HOUR,
    price_type=PriceType.LAST,
)

daily_bar_type = BarType(
    instrument_id=InstrumentId("BTCUSDT.BINANCE"),
    bar_spec=1,
    aggregation=BarAggregation.DAY,
    price_type=PriceType.LAST,
)

# Create the strategy configuration
config = MeanReversionStrategyConfig(
    instrument_id=InstrumentId("BTCUSDT.BINANCE"),
    bar_type=hourly_bar_type,
    trade_size=Decimal("0.1"),
    lookback=168,  # 7 days of hourly data
    std_dev_threshold=2.0,
    positions_per_side=3,
)
```

### Usage

```python
from src.strategies.mean_reversion import MeanReversionStrategy

# Create the strategy
strategy = MeanReversionStrategy(config=config)

# Add to a trading engine
engine.add_strategy(strategy=strategy)
```

## Creating New Strategies

To create a new strategy:

1. Create a new directory in the `src/strategies/` directory
2. Create a configuration class that inherits from `StrategyConfig`
3. Create a strategy class that inherits from `Strategy`
4. Implement the required methods:
   - `on_start`
   - `on_stop`
   - `on_reset`
   - `on_save`
   - `on_load`
   - `on_event`
   - `on_data`

Example:

```python
from nautilus_trader.config import StrategyConfig
from nautilus_trader.trading.strategy import Strategy

class MyStrategyConfig(StrategyConfig):
    instrument_id: InstrumentId
    bar_type: BarType
    # Add your configuration parameters

class MyStrategy(Strategy):
    def __init__(self, config: MyStrategyConfig):
        super().__init__(config)
        # Initialize your strategy

    def on_start(self):
        # Actions to perform when the strategy is started

    def on_stop(self):
        # Actions to perform when the strategy is stopped

    def on_reset(self):
        # Actions to perform when the strategy is reset

    def on_save(self):
        # Save the strategy state

    def on_load(self, state):
        # Load the strategy state

    def on_event(self, event):
        # Handle events

    def on_data(self, data):
        # Handle data
```
