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
Entry point for running a live trading node.
"""

import argparse
import logging
import sys
from pathlib import Path

from nautilus_trader.config import LiveRunConfig
from nautilus_trader.live.node import LiveNode


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Run a live trading node")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to the configuration file",
    )
    parser.add_argument(
        "--paper",
        action="store_true",
        help="Run in paper trading mode",
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
    Run the live trading node.
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
        config = LiveRunConfig.from_yaml(str(config_path))
    else:
        # Use default configuration
        logger.info("Using default configuration")
        # This is a placeholder - implement your default config logic
        config = LiveRunConfig()
    
    # Set paper trading mode if requested
    if args.paper:
        logger.info("Running in paper trading mode")
        # Modify config for paper trading
        # This is a placeholder - implement your paper trading config logic
    
    try:
        # Initialize and run the live node
        node = LiveNode(configs=[config])
        node.run()
    except Exception as e:
        logger.exception(f"Error running live node: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
