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

    python scripts/download_data.py --symbols BTCUSDT --timeframes 1h 1d

This will download the data and write it directly to the Nautilus Trader catalog
at data/catalog, which is used by this script.

You can run a backtest with a specific strategy by providing the path to its
configuration file:

    python src/main_backtest.py --strategy src/strategies/mean_reversion/config.yaml

Or run multiple strategies at once:

    python src/main_backtest.py --strategy src/strategies/mean_reversion/config.yaml src/strategies/moving_average_crossover/config.yaml
"""

import argparse
import logging
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add the current directory to the Python path
sys.path.insert(0, os.getcwd())

from nautilus_trader.backtest.node import BacktestNode, BacktestDataConfig, BacktestVenueConfig
from nautilus_trader.config import BacktestRunConfig, BacktestEngineConfig, ImportableStrategyConfig
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
        help="Path to the backtest configuration file",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        nargs="+",
        default=None,
        help="Path(s) to strategy configuration file(s)",
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


def load_strategy_config(config_path: str) -> Dict[str, Any]:
    """
    Load a strategy configuration from a YAML file.

    Parameters
    ----------
    config_path : str
        Path to the strategy configuration file.

    Returns
    -------
    Dict[str, Any]
        The strategy configuration.
    """
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def create_importable_strategy_config(config_path: str) -> ImportableStrategyConfig:
    """
    Create an ImportableStrategyConfig from a strategy configuration file.

    Parameters
    ----------
    config_path : str
        Path to the strategy configuration file.

    Returns
    -------
    ImportableStrategyConfig
        The importable strategy configuration.
    """
    config_dict = load_strategy_config(config_path)

    strategy_info = config_dict.get("strategy", {})
    strategy_module = strategy_info.get("module")
    strategy_class = strategy_info.get("class")
    config_class = strategy_info.get("config_class")

    if not strategy_module or not strategy_class or not config_class:
        raise ValueError(f"Invalid strategy configuration in {config_path}")

    # Create the importable strategy config
    return ImportableStrategyConfig(
        strategy_path=f"{strategy_module}:{strategy_class}",
        config_path=f"{strategy_module}:{config_class}",
        config=config_dict.get("parameters", {}),
    )


def create_data_configs(strategy_configs: List[str], start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[BacktestDataConfig]:
    """
    Create data configurations from strategy configuration files.

    Parameters
    ----------
    strategy_configs : List[str]
        Paths to strategy configuration files.
    start_date : Optional[str]
        Start date for the backtest.
    end_date : Optional[str]
        End date for the backtest.

    Returns
    -------
    List[BacktestDataConfig]
        The data configurations.
    """
    from nautilus_trader.model.data import Bar

    data_configs = []
    processed_instruments = set()

    for config_path in strategy_configs:
        config_dict = load_strategy_config(config_path)
        data_config = config_dict.get("data", {})
        instruments = data_config.get("instruments", [])

        for instrument in instruments:
            instrument_id = instrument.get("id")
            if not instrument_id or instrument_id in processed_instruments:
                continue

            processed_instruments.add(instrument_id)
            bar_types = instrument.get("bar_types", [])

            for bar_spec in bar_types:
                data_configs.append(
                    BacktestDataConfig(
                        catalog_path="data/catalog",
                        data_cls=Bar,
                        instrument_id=instrument_id,
                        bar_spec=bar_spec,
                        start_time=start_date,
                        end_time=end_date,
                    )
                )

    return data_configs


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
    elif args.strategy:
        # Load strategy configurations
        strategy_paths = args.strategy
        strategies = []

        for path in strategy_paths:
            strategy_path = Path(path)
            if not strategy_path.exists():
                logger.error(f"Strategy configuration file not found: {strategy_path}")
                sys.exit(1)

            try:
                strategy_config = create_importable_strategy_config(str(strategy_path))
                strategies.append(strategy_config)
                logger.info(f"Loaded strategy configuration from {strategy_path}")
            except Exception as e:
                logger.error(f"Error loading strategy configuration from {strategy_path}: {e}")
                sys.exit(1)

        # Create data configurations
        data_configs = create_data_configs(
            strategy_paths,
            start_date=args.start_date,
            end_date=args.end_date,
        )

        # Create venue configuration
        venue_configs = [
            BacktestVenueConfig(
                name="BINANCE",
                oms_type="NETTING",
                account_type="MARGIN",
                base_currency=USDT,
                starting_balances=["1000000 USDT"],
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
    else:
        # Use default configuration with Mean Reversion strategy
        logger.info("No strategy specified, using default Mean Reversion strategy")

        default_strategy_path = "src/strategies/mean_reversion/config.yaml"
        if not Path(default_strategy_path).exists():
            logger.error(f"Default strategy configuration file not found: {default_strategy_path}")
            sys.exit(1)

        try:
            strategy_config = create_importable_strategy_config(default_strategy_path)
            strategies = [strategy_config]
            logger.info(f"Loaded default strategy configuration from {default_strategy_path}")
        except Exception as e:
            logger.error(f"Error loading default strategy configuration: {e}")
            sys.exit(1)

        # Create data configurations
        data_configs = create_data_configs(
            [default_strategy_path],
            start_date=args.start_date,
            end_date=args.end_date,
        )

        # Create venue configuration
        venue_configs = [
            BacktestVenueConfig(
                name="BINANCE",
                oms_type="NETTING",
                account_type="MARGIN",
                base_currency=USDT,
                starting_balances=["1000000 USDT"],
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
        node.run()

        # Print summary results
        logger.info("Backtest completed successfully")
    except Exception as e:
        logger.exception(f"Error running backtest: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
