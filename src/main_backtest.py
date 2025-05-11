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
Entry point for running a backtest node.

Before running this script, make sure you have downloaded the required data
using the scripts/download_data.py script:

    python scripts/download_data.py --symbols BTCUSDT --timeframes 1h

This will download the data and write it directly to the Nautilus Trader catalog
at data/catalog, which is used by this script.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, os.getcwd())

from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import BacktestRunConfig, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import USDT


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Run a backtest node")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to the configuration file",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Start date for backtest (format: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date for backtest (format: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    return parser.parse_args()


def main() -> None:
    """
    Run the backtest node.
    """
    args = parse_args()

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Load configuration
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)

        # Load configuration from file
        config = BacktestRunConfig.from_yaml(str(config_path))
    else:
        # Use default configuration with Moving Average Crossover strategy
        logger.info("Using default configuration with Moving Average Crossover strategy")

        from decimal import Decimal
        from nautilus_trader.config import ImportableStrategyConfig
        from nautilus_trader.backtest.node import BacktestDataConfig, BacktestVenueConfig

        # Define the instrument ID
        instrument_id = "BTCUSDT.BINANCE"

        # Define the bar type
        bar_type = f"{instrument_id}-1-HOUR-LAST-EXTERNAL"

        # Create strategy configuration
        strategies = [
            ImportableStrategyConfig(
                strategy_path="src.strategies.moving_average_crossover:MovingAverageCrossover",
                config_path="src.strategies.moving_average_crossover:MovingAverageCrossoverConfig",
                config={
                    "instrument_id": instrument_id,
                    "bar_type": bar_type,
                    "fast_ema_period": 10,
                    "slow_ema_period": 20,
                    "trade_size": Decimal("0.1"),
                },
            ),
        ]

        # Create data configuration
        from nautilus_trader.model.data import Bar

        # We'll use the data from the Nautilus Trader catalog
        data_configs = [
            BacktestDataConfig(
                catalog_path="data/catalog",
                data_cls=Bar,
                instrument_id=instrument_id,
                bar_spec="1-HOUR",
            ),
        ]

        # Create venue configuration
        venue_configs = [
            BacktestVenueConfig(
                name="BINANCE",
                oms_type="NETTING",
                account_type="MARGIN",
                base_currency=USDT,  # Use None for multi-currency account
                starting_balances=["1000000 USDT"],  # Include both currencies
            ),
        ]

        # Create the backtest run configuration
        config = BacktestRunConfig(
            engine=BacktestEngineConfig(
                strategies=strategies,
                logging=LoggingConfig(log_level=args.log_level),
            ),
            data=data_configs,
            venues=venue_configs,
        )

    # Override start and end dates if provided
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
            config.engine.start_time = start_date
            logger.info(f"Using start date: {start_date}")
        except ValueError:
            logger.error(f"Invalid start date format: {args.start_date}. Expected YYYY-MM-DD")
            sys.exit(1)

    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
            config.engine.end_time = end_date
            logger.info(f"Using end date: {end_date}")
        except ValueError:
            logger.error(f"Invalid end date format: {args.end_date}. Expected YYYY-MM-DD")
            sys.exit(1)

    try:
        # Initialize and run the backtest node
        node = BacktestNode(configs=[config])
        result = node.run()

        # Print summary results
        logger.info("Backtest completed successfully")
    except Exception as e:
        logger.exception(f"Error running backtest: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
