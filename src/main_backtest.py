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

    python src/main_backtest.py --strategy src/strategies/moving_average_crossover/config.yaml

Or run multiple strategies at once:

    python src/main_backtest.py --strategy src/strategies/moving_average_crossover/config.yaml src/strategies/moving_average_crossover/config.yaml

Additional options:
    --benchmark SYMBOL    Compare strategy performance against a benchmark (e.g., 'SPY', 'BTC-USD')
    --output-dir DIR      Directory to save the QuantStats report (default: 'backtest_reports')
    --open-browser        Open the generated report in a browser automatically
    --start-date DATE     Start date for backtest (format: YYYY-MM-DD)
    --end-date DATE       End date for backtest (format: YYYY-MM-DD)
    --log-level LEVEL     Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

Example with visualization:
    python src/main_backtest.py --strategy src/strategies/moving_average_crossover/config.yaml --benchmark BTC-USD --open-browser

"""

import argparse
import logging
import os
import sys
import yaml
import numpy as np
import pandas as pd
import quantstats as qs
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add the current directory to the Python path
sys.path.insert(0, os.getcwd())

from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.config import BacktestDataConfig, BacktestVenueConfig
from nautilus_trader.backtest.models import FillModel
from nautilus_trader.config import BacktestRunConfig, BacktestEngineConfig, ImportableStrategyConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.identifiers import Venue


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
        "--benchmark",
        type=str,
        default=None,
        help="Benchmark ticker symbol for comparison (e.g., 'SPY', 'BTC-USD')",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="backtest_reports",
        help="Directory to save the QuantStats report (default: 'backtest_reports')",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open the generated report in a browser automatically",
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
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
            config = BacktestRunConfig(**config_dict)
    elif args.strategy:
        # Load strategy configurations
        strategy_paths = args.strategy
    else:
        # Use default configuration with Moving Average Crossover strategy
        logger.info("No strategy specified, using default Moving Average Crossover strategy")
        strategy_paths = ["src/strategies/moving_average_crossover/config.yaml"]

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

    # Create a fill model with optimal parameters
    fill_model = FillModel(
        prob_fill_on_limit=1.0,  # 100% chance of limit orders filling when price matches
        prob_fill_on_stop=1.0,   # 100% chance of stop orders filling when price matches
        prob_slippage=0.0,       # 0% chance of slippage
        random_seed=42,          # For reproducibility
    )

    # Create venue configuration with L1_MBP book type for bar data
    venue_configs = [
        BacktestVenueConfig(
            name="BINANCE",
            oms_type="NETTING",
            account_type="MARGIN",
            base_currency=None,
            starting_balances=["1000000 USDT"],
            book_type="L1_MBP",     # Use L1 Market-by-Price for bar data
            bar_adaptive_high_low_ordering=True,
        ),
    ]

    # Process start and end dates
    start_time = None
    end_time = None

    if args.start_date:
        try:
            start_time = datetime.strptime(args.start_date, "%Y-%m-%d")
            logger.info(f"Using start date: {start_time}")
        except ValueError:
            logger.error(f"Invalid start date format: {args.start_date}. Expected YYYY-MM-DD")
            sys.exit(1)

    if args.end_date:
        try:
            end_time = datetime.strptime(args.end_date, "%Y-%m-%d")
            logger.info(f"Using end date: {end_time}")
        except ValueError:
            logger.error(f"Invalid end date format: {args.end_date}. Expected YYYY-MM-DD")
            sys.exit(1)

    # Create the backtest run configuration
    config = BacktestRunConfig(
        engine=BacktestEngineConfig(
            trader_id="BACKTESTER-001",
            strategies=strategies,
            logging=LoggingConfig(log_level=args.log_level),
        ),
        data=data_configs,
        venues=venue_configs,
    )

    try:
        # Initialize and run the backtest node
        node = BacktestNode(configs=[config])

        # Get the engine from the node
        engine: BacktestEngine = node.get_engine(config.id)

        # # Set the fill model for the BINANCE venue
        # if engine is not None:
        #     engine.change_fill_model(venue=Venue("BINANCE"), model=fill_model)
        # else:
        #     logger.error("Could not get engine from node, fill model not applied")
        #     # raise Exception("Could not get engine from node, fill model not applied")

        # Run the backtest
        results = node.run()
        print("Backtest completed successfully")

        # Get the engine from the node
        engine: BacktestEngine = node.get_engine(config.id)

        # Get daily returns
        # Access the portfolio directly from the engine instead of through trader
        returns = engine.portfolio.analyzer.returns()
        print("Daily Returns:")
        print(returns)

        # Get returns statistics
        returns_stats = engine.portfolio.analyzer.get_performance_stats_returns()
        print("\nReturns Statistics:")
        for stat_name, stat_value in returns_stats.items():
            print(f"{stat_name}: {stat_value}")

        # Get filled orders
        order_fills_df = engine.trader.generate_order_fills_report()
        print("\nOrder Fills:")
        print(order_fills_df)

        # Get positions
        positions_df = engine.trader.generate_positions_report()
        print("\nPositions:")
        print(positions_df)

        # Get account information (replace "VENUE_NAME" with your venue)
        venue_name = "BINANCE"  # or whatever venue you're using
        account_df = engine.trader.generate_account_report(Venue(venue_name))
        print(f"\nAccount Report for {venue_name}:")
        print(account_df)

        # Get the backtest result
        if results and len(results) > 0:
            backtest_result = results[0]
            print(f"Backtest results retrieved successfully: {backtest_result}")

            # Get the backtest start and end dates
            if backtest_result.backtest_start:
                start_date = pd.Timestamp(backtest_result.backtest_start / 1_000_000_000, unit='s')
            else:
                start_date = pd.Timestamp('2020-01-01')

            if backtest_result.backtest_end:
                end_date = pd.Timestamp(backtest_result.backtest_end / 1_000_000_000, unit='s')
            else:
                end_date = pd.Timestamp.now()

            print(f"Backtest period: {start_date} to {end_date}")

            # Generate output directory if it doesn't exist
            output_dir = Path(args.output_dir)
            output_dir.mkdir(exist_ok=True, parents=True)

            # Generate a filename based on strategy and timestamp
            strategy_name = Path(strategy_paths[0]).stem if strategy_paths else "unknown_strategy"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"{strategy_name}_{timestamp}_report.html"

            print(f"Generating QuantStats report to {output_file}")

            # Generate a full QuantStats report
            try:
                # Generate the report with error handling
                try:
                    trimed_returns = returns[1:]
                    returns_series = trimed_returns.tz_localize(None).resample('D').sum().fillna(0)
                    print(f"Returns series: {returns_series}")
        
                    qs.reports.full(returns_series, benchmark=args.benchmark, output=str(output_file), title=f"Backtest Results for {strategy_name}")
                    print(f"QuantStats report generated successfully at {output_file}")

                    # Open the report in a browser if requested
                    if args.open_browser:
                        print(f"Opening report in browser")
                        webbrowser.open(f"file://{output_file.absolute()}")

                except Exception as e:
                    print(f"Error generating full report: {e}")
            except Exception as e:
                print(f"Failed to generate any report: {e}")
        else:
            print("No backtest results returned")

    except Exception as e:
        print(f"Error running backtest: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
