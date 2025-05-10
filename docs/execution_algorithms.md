# Execution Algorithms

This document describes the execution algorithms available in the Nautilus Playground project.

## Available Algorithms

- `twap.py`: Time-Weighted Average Price (TWAP) execution algorithm

## TWAP Algorithm

The TWAP algorithm splits a large order into smaller slices and executes them at regular time intervals to minimize market impact.

### Configuration

```python
from decimal import Decimal
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from src.execution.twap import TWAPConfig

config = TWAPConfig(
    instrument_id=InstrumentId("BTCUSDT.BINANCE"),
    order_side=OrderSide.BUY,
    total_quantity=Decimal("1.0"),
    num_slices=10,
    time_interval_seconds=60,
    limit_offset_ticks=None,  # Use market orders
)
```

### Usage

```python
from nautilus_trader.model.identifiers import StrategyId, TraderId
from src.execution.twap import TWAP

twap = TWAP(
    trader_id=TraderId("TRADER-001"),
    strategy_id=StrategyId("STRATEGY-001"),
    config=config,
)

# Add to a strategy
self.register_execution_algorithm(twap)
```

## Creating New Execution Algorithms

To create a new execution algorithm:

1. Create a new Python file in the `src/execution/` directory
2. Inherit from `ExecutionAlgorithm`
3. Implement the required methods:
   - `on_start`
   - `on_stop`
   - `on_event`
   - `on_data`

Example:

```python
from nautilus_trader.execution.algorithm import ExecutionAlgorithm

class MyExecutionAlgorithm(ExecutionAlgorithm):
    def __init__(self, trader_id, strategy_id, config):
        super().__init__(trader_id, strategy_id)
        # Initialize your algorithm
        
    def on_start(self):
        # Actions to perform when the algorithm is started
        
    def on_stop(self):
        # Actions to perform when the algorithm is stopped
        
    def on_event(self, event):
        # Handle events
        
    def on_data(self, data):
        # Handle data
```
