# Data Catalog

This document describes the local data catalog for the Nautilus Playground project. The catalog provides a consistent and reproducible source of data for backtesting and examples.

## Directory Structure

The catalog is organized by data source and symbol:

```
data/catalog/
├── binance/
│   ├── BTCUSDT/
│   │   ├── BTCUSDT_1h.csv
│   │   ├── BTCUSDT_1h_metadata.json
│   │   ├── BTCUSDT_4h.csv
│   │   └── BTCUSDT_4h_metadata.json
│   ├── ETHUSDT/
│   │   ├── ETHUSDT_1h.csv
│   │   └── ...
│   └── ...
├── other_source/
│   └── ...
```

## Data Sources

### Binance

The Binance data is downloaded using the `scripts/download_data.py` script. It includes historical price data for various symbols and timeframes.

To download Binance data:

```bash
python scripts/download_data.py --symbols BTCUSDT ETHUSDT --timeframes 1h 4h
```

## Data Format

### CSV Files

The CSV files contain historical price data with the following columns:

- `timestamp`: The timestamp of the bar (used as index)
- `open`: Opening price
- `high`: Highest price
- `low`: Lowest price
- `close`: Closing price
- `volume`: Volume
- `close_time`: Close time
- `quote_asset_volume`: Quote asset volume
- `number_of_trades`: Number of trades
- `taker_buy_base_asset_volume`: Taker buy base asset volume
- `taker_buy_quote_asset_volume`: Taker buy quote asset volume

### Metadata Files

Each data file has a corresponding metadata JSON file with information about the data:

```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "start_date": "2023-04-01T00:00:00",
  "end_date": "2023-05-01T00:00:00",
  "rows": 720,
  "columns": ["open", "high", "low", "close", "volume", "close_time", "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume"],
  "source": "Binance",
  "download_date": "2023-05-02T10:15:30"
}
```

## Using the Catalog

### In Python Code

```python
import pandas as pd

# Load data from the catalog
data_path = "data/catalog/binance/BTCUSDT/BTCUSDT_1h.csv"
df = pd.read_csv(data_path, index_col=0, parse_dates=True)
```

### In Nautilus Trader

```python
from pathlib import Path
from nautilus_trader.backtest.data import BacktestDataConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId

# Define the bar type
bar_type = BarType(
    instrument_id=InstrumentId("BTCUSDT.BINANCE"),
    bar_spec=1,
    aggregation=BarAggregation.HOUR,
    price_type=PriceType.LAST,
)

# Create data config
data_config = BacktestDataConfig(
    catalog_path=Path("data/catalog"),
    data_cls="Bar",
    instrument_id="BTCUSDT.BINANCE",
    bar_type=bar_type,
)

# Add to backtest engine
engine.add_data(data_config)
```

## Adding New Data

To add new data to the catalog:

1. Create a directory for the data source if it doesn't exist
2. Create a directory for the symbol if it doesn't exist
3. Save the data as a CSV file with a descriptive name
4. Create a metadata JSON file with the same base name

Example:

```
data/catalog/new_source/SYMBOL/SYMBOL_timeframe.csv
data/catalog/new_source/SYMBOL/SYMBOL_timeframe_metadata.json
```
