# Utility Scripts

This document describes the utility scripts available in the Nautilus Playground project.

## Available Scripts

- `download_data.py`: Script to download sample data from Binance
- `update_nautilus.py`: Script to update the Nautilus Trader documentation

## Download Data Script

The `download_data.py` script downloads historical price data from Binance for use in backtesting and examples.

### Usage

```bash
python scripts/download_data.py
```

By default, this will download data for the following:
- Symbols: BTCUSDT, ETHUSDT, BNBUSDT
- Timeframes: 1m, 5m, 15m, 1h, 4h, 1d
- Last 30 days of data

### Custom Parameters

You can customize the download with the following parameters:

```bash
python scripts/download_data.py --symbols BTCUSDT ETHUSDT --timeframes 1h 4h --days 60
```

Available parameters:
- `--symbols`: List of symbols to download (e.g., BTCUSDT, ETHUSDT)
- `--timeframes`: List of timeframes to download (e.g., 1m, 5m, 15m, 1h, 4h, 1d)
- `--days`: Number of days of historical data to download
- `--output-dir`: Output directory for downloaded data (default: data/catalog/binance)
- `--log-level`: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Output

The script saves the downloaded data to CSV files in the specified output directory, organized by symbol:

```
data/catalog/binance/
├── BTCUSDT/
│   ├── BTCUSDT_1h.csv
│   ├── BTCUSDT_1h_metadata.json
│   ├── BTCUSDT_4h.csv
│   └── BTCUSDT_4h_metadata.json
├── ETHUSDT/
│   ├── ETHUSDT_1h.csv
│   ├── ETHUSDT_1h_metadata.json
│   ├── ETHUSDT_4h.csv
│   └── ETHUSDT_4h_metadata.json
```

Each CSV file contains the following columns:
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

Each data file also has a corresponding metadata JSON file with information about the data, including:
- `symbol`: The trading pair symbol
- `interval`: The timeframe interval
- `start_date`: The start date of the data
- `end_date`: The end date of the data
- `rows`: The number of rows in the data
- `columns`: The columns in the data
- `source`: The data source (Binance)
- `download_date`: The date the data was downloaded

## Update Nautilus Script

The `update_nautilus.py` script updates the Nautilus Trader documentation in the `docs/nautilus` directory. This script is automatically executed during the Docker build process to ensure that the Nautilus Trader docs are included in the container image. It can also be run manually to update the docs.

### Usage

```bash
python scripts/update_nautilus.py
```

### Custom Parameters

You can customize the update process with the following parameters:

```bash
python scripts/update_nautilus.py --repository nautechsystems/nautilus_trader --branch develop
```

Available parameters:
- `--repository`: Repository to clone (default: nautechsystems/nautilus_trader)
- `--branch`: Branch to clone (default: develop)
- `--docs-path`: Path to docs in the repository (default: docs)
- `--docs-destination`: Destination path for docs (default: docs/nautilus)
- `--clone-location`: Location where the repository will be cloned (default: ../nautilus_trader)
- `--temp-dir`: Temporary directory for cloning (default: system temp dir)
- `--log-level`: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Creating New Scripts

To create a new utility script:

1. Create a new Python file in the `scripts` directory
2. Add a shebang line: `#!/usr/bin/env python3`
3. Add the copyright notice
4. Add a docstring describing the script's purpose
5. Implement the script with a `main()` function
6. Add command-line argument parsing using `argparse`
7. Make the script executable: `chmod +x script_name.py`

Example:

```python
#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2023 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

"""
Description of the script.
"""

import argparse
import logging
import sys


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("--arg", type=str, help="Argument description")
    return parser.parse_args()


def main() -> None:
    """
    Main entry point.
    """
    args = parse_args()
    # Implement your script logic here


if __name__ == "__main__":
    main()
```
