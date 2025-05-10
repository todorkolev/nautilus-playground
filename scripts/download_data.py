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
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default symbols and timeframes to download
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]
DEFAULT_DAYS = 30

# Binance API endpoints
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Download sample data from Binance")
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
        "--output-dir",
        type=str,
        default="data/catalog/binance",
        help="Output directory for downloaded data (default: data/catalog/binance)",
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


def download_historical_data(
    symbol: str,
    interval: str,
    days: int,
    output_dir: Path,
) -> None:
    """
    Download historical kline data for a symbol and interval.
    
    Parameters
    ----------
    symbol : str
        Trading pair symbol
    interval : str
        Kline interval (e.g., "1m", "5m", "1h")
    days : int
        Number of days of historical data to download
    output_dir : Path
        Output directory for downloaded data
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
    
    # Create output directory
    symbol_dir = output_dir / symbol
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
    Main entry point for downloading data.
    """
    args = parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
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
                    output_dir=output_dir,
                )
            except Exception as e:
                logger.error(f"Error downloading {symbol} {timeframe}: {e}")
    
    logger.info(f"Data download completed. Files saved to {output_dir}")


if __name__ == "__main__":
    main()
