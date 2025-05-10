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
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import BacktestRunConfig, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig


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
        # This is a placeholder - implement your config loading logic
        config = BacktestRunConfig.from_yaml(str(config_path))
    else:
        # Use default configuration
        logger.info("Using default configuration")
        # This is a placeholder - implement your default config logic
        config = BacktestRunConfig(
            engine=BacktestEngineConfig(
                strategies=[],  # Add your strategies here
                logging=LoggingConfig(log_level=args.log_level),
            ),
            data=[],  # Add your data sources here
            venues=[],  # Add your venues here
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
        logger.info(f"Results: {result}")
    except Exception as e:
        logger.exception(f"Error running backtest: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
