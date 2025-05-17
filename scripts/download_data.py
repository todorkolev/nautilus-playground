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
Script to download sample data from Binance for use with the Nautilus Playground.
Data is written directly to the Nautilus Trader Catalog for use in backtesting.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests

from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import BarAggregation
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.persistence.catalog import ParquetDataCatalog


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default symbols and timeframes to download
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"]
DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]
DEFAULT_DAYS = 30

# Binance API endpoints
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Download sample data from Binance and write to Nautilus Catalog")
    parser.add_argument(
        "--symbols",
        type=str,
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help=f"Symbols to download (default: {DEFAULT_SYMBOLS})",
    )
    parser.add_argument(
        "--timeframes",
        type=str,
        nargs="+",
        default=DEFAULT_TIMEFRAMES,
        help=f"Timeframes to download (default: {DEFAULT_TIMEFRAMES})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help=f"Number of days of historical data to download (default: {DEFAULT_DAYS})",
    )
    parser.add_argument(
        "--catalog-path",
        type=str,
        default="data/catalog",
        help="Path to the Nautilus Trader catalog (default: data/catalog)",
    )
    parser.add_argument(
        "--save-csv",
        action="store_true",
        help="Also save data as CSV files in addition to writing to the catalog",
    )
    parser.add_argument(
        "--csv-dir",
        type=str,
        default="data/catalog/binance",
        help="Output directory for CSV files if --save-csv is used (default: data/catalog/binance)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    return parser.parse_args()


def get_exchange_info() -> Dict:
    """
    Get exchange information from Binance.

    Returns
    -------
    Dict
        Exchange information
    """
    try:
        response = requests.get(BINANCE_EXCHANGE_INFO_URL)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get exchange info: {e}")
        return {}


def download_klines(
    symbol: str,
    interval: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 1000,
) -> List:
    """
    Download klines (candlestick data) from Binance.

    Parameters
    ----------
    symbol : str
        Trading pair symbol
    interval : str
        Kline interval (e.g., "1m", "5m", "1h")
    start_time : Optional[int]
        Start time in milliseconds
    end_time : Optional[int]
        End time in milliseconds
    limit : int
        Maximum number of klines to return

    Returns
    -------
    List
        List of klines
    """
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }

    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    try:
        response = requests.get(BINANCE_KLINES_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to download klines for {symbol} {interval}: {e}")
        return []


def create_instrument(symbol: str) -> Instrument:
    """
    Create a Nautilus Trader instrument for a Binance symbol.

    Parameters
    ----------
    symbol : str
        Trading pair symbol (e.g., "BTCUSDT")

    Returns
    -------
    Instrument
        The created instrument
    """
    from nautilus_trader.test_kit.providers import TestInstrumentProvider

    # Create instrument ID
    instrument_id = InstrumentId(Symbol(symbol), Venue("BINANCE"))

    # Use TestInstrumentProvider for simplicity
    if symbol == "BTCUSDT":
        instrument = TestInstrumentProvider.btcusdt_binance()
    elif symbol == "ETHUSDT":
        instrument = TestInstrumentProvider.ethusdt_binance()
    else:
        # For other symbols, create a generic instrument
        instrument = TestInstrumentProvider.btcusdt_binance()
        # Update the instrument ID
        instrument._instrument_id = instrument_id

    return instrument


def download_historical_data(
    symbol: str,
    interval: str,
    days: int,
    catalog: ParquetDataCatalog,
    save_csv: bool = False,
    csv_dir: Optional[Path] = None,
) -> None:
    """
    Download historical kline data for a symbol and interval and write to Nautilus Catalog.

    Parameters
    ----------
    symbol : str
        Trading pair symbol
    interval : str
        Kline interval (e.g., "1m", "5m", "1h")
    days : int
        Number of days of historical data to download
    catalog : ParquetDataCatalog
        The Nautilus Trader catalog to write data to
    save_csv : bool, optional
        Whether to also save data as CSV files
    csv_dir : Optional[Path], optional
        Output directory for CSV files if save_csv is True
    """
    # Calculate start and end times
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    # Convert to milliseconds timestamp
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)

    logger.info(f"Downloading {days} days of {interval} data for {symbol}")

    all_klines = []
    current_start = start_ms

    # Download data in chunks
    while current_start < end_ms:
        klines = download_klines(
            symbol=symbol,
            interval=interval,
            start_time=current_start,
            end_time=end_ms,
            limit=1000,
        )

        if not klines:
            break

        all_klines.extend(klines)

        # Update start time for next chunk
        current_start = int(klines[-1][0]) + 1

        logger.debug(f"Downloaded {len(klines)} klines, total: {len(all_klines)}")

    if not all_klines:
        logger.warning(f"No data downloaded for {symbol} {interval}")
        return

    # Convert to DataFrame
    df = pd.DataFrame(
        all_klines,
        columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore",
        ],
    )

    # Convert timestamp to datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    # Set timestamp as index
    df.set_index("timestamp", inplace=True)

    # Convert numeric columns
    numeric_columns = ["open", "high", "low", "close", "volume", "quote_asset_volume",
                      "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume"]
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)

    # Create and write instrument to catalog
    instrument = create_instrument(symbol)
    catalog.write_data([instrument])
    logger.info(f"Wrote instrument {instrument.id} to catalog")

    # Map interval to BarAggregation
    interval_map = {
        "1m": (1, BarAggregation.MINUTE),
        "5m": (5, BarAggregation.MINUTE),
        "15m": (15, BarAggregation.MINUTE),
        "30m": (30, BarAggregation.MINUTE),
        "1h": (1, BarAggregation.HOUR),
        "2h": (2, BarAggregation.HOUR),
        "4h": (4, BarAggregation.HOUR),
        "6h": (6, BarAggregation.HOUR),
        "8h": (8, BarAggregation.HOUR),
        "12h": (12, BarAggregation.HOUR),
        "1d": (1, BarAggregation.DAY),
        "3d": (3, BarAggregation.DAY),
        "1w": (1, BarAggregation.WEEK),
        "1M": (1, BarAggregation.MONTH),
    }

    # Get bar spec and aggregation
    if interval in interval_map:
        bar_spec, aggregation = interval_map[interval]
    else:
        logger.warning(f"Unknown interval {interval}, defaulting to 1-HOUR")
        bar_spec, aggregation = 1, BarAggregation.HOUR

    # Create bar type
    bar_type_str = f"{instrument.id.value}-{bar_spec}-{aggregation.name}-LAST-EXTERNAL"
    bar_type = BarType.from_str(bar_type_str)

    # Create bars
    bars = []
    for timestamp, row in df.iterrows():
        # Convert timestamp to nanoseconds
        ts_event = int(timestamp.timestamp() * 1_000_000_000)

        # Create bar
        try:
            # Ensure volume has exactly 6 decimal places precision
            volume_str = f"{float(row['volume']):.6f}"
            open_price = f"{float(row['open']):.2f}"
            high_price = f"{float(row['high']):.2f}"
            low_price = f"{float(row['low']):.2f}"
            close_price = f"{float(row['close']):.2f}"

            bar = Bar(
                bar_type=bar_type,
                open=Price.from_str(open_price),
                high=Price.from_str(high_price),
                low=Price.from_str(low_price),
                close=Price.from_str(close_price),
                volume=Quantity.from_str(volume_str),
                ts_event=ts_event,
                ts_init=ts_event,  # Use same timestamp for simplicity
            )
            bars.append(bar)
        except Exception as e:
            logger.warning(f"Error creating bar for {timestamp}: {e}")

    # Write bars to catalog
    catalog.write_data(bars)
    logger.info(f"Wrote {len(bars)} bars to catalog for {symbol} {interval}")

    # Save to CSV if requested
    if save_csv and csv_dir:
        # Create output directory
        symbol_dir = csv_dir / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)

        # Save to CSV
        csv_path = symbol_dir / f"{symbol}_{interval}.csv"
        df.to_csv(csv_path)

        # Save metadata
        metadata = {
            "symbol": symbol,
            "interval": interval,
            "start_date": start_time.isoformat(),
            "end_date": end_time.isoformat(),
            "rows": len(df),
            "columns": list(df.columns),
            "source": "Binance",
            "download_date": datetime.now().isoformat(),
        }

        metadata_path = symbol_dir / f"{symbol}_{interval}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved {len(df)} rows to {csv_path}")


def main() -> None:
    """
    Main entry point for downloading data and writing to Nautilus Catalog.
    """
    args = parse_args()

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Create catalog directory
    catalog_path = Path(args.catalog_path)
    catalog_path.mkdir(parents=True, exist_ok=True)

    # Create catalog
    catalog = ParquetDataCatalog(str(catalog_path))
    logger.info(f"Created Nautilus Trader catalog at {catalog_path}")

    # Create CSV directory if needed
    csv_dir = None
    if args.save_csv:
        csv_dir = Path(args.csv_dir)
        csv_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CSV files will be saved to {csv_dir}")

    # Get exchange info to validate symbols
    exchange_info = get_exchange_info()
    valid_symbols = set()

    if exchange_info and "symbols" in exchange_info:
        valid_symbols = {s["symbol"] for s in exchange_info["symbols"]}

    # Filter valid symbols
    symbols_to_download = []
    for symbol in args.symbols:
        if not valid_symbols or symbol in valid_symbols:
            symbols_to_download.append(symbol)
        else:
            logger.warning(f"Invalid symbol: {symbol}")

    if not symbols_to_download:
        logger.error("No valid symbols to download")
        sys.exit(1)

    # Download data for each symbol and timeframe
    for symbol in symbols_to_download:
        for timeframe in args.timeframes:
            try:
                download_historical_data(
                    symbol=symbol,
                    interval=timeframe,
                    days=args.days,
                    catalog=catalog,
                    save_csv=args.save_csv,
                    csv_dir=csv_dir,
                )
            except Exception as e:
                logger.error(f"Error downloading {symbol} {timeframe}: {e}")

    logger.info(f"Data download completed. Data written to Nautilus Trader catalog at {catalog_path}")

    # Print information about how to use the data in backtests
    logger.info("\nTo use this data in backtests, configure your BacktestDataConfig like this:")
    logger.info(f"""
    from nautilus_trader.backtest.node import BacktestDataConfig
    from nautilus_trader.model.data import Bar

    data_configs = [
        BacktestDataConfig(
            catalog_path="{args.catalog_path}",
            data_cls=Bar,
            instrument_id="SYMBOL.BINANCE",  # Replace with your symbol
            bar_spec="1-HOUR",  # Adjust based on your timeframe
        ),
    ]
    """)


if __name__ == "__main__":
    main()
