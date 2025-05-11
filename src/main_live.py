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

Before running this script, make sure you have set up your Binance API credentials
in a .env file. You can use the .env.example file as a template:

    cp .env.example .env
    # Edit .env with your API credentials

To run in live trading mode:
    python src/main_live.py

To run in paper trading mode:
    python src/main_live.py --paper

To use a custom configuration file:
    python src/main_live.py --config path/to/config.yaml
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Try to import dotenv for loading environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("python-dotenv not installed. Environment variables must be set manually.")

from nautilus_trader.adapters.binance.common.enums import BinanceAccountType
from nautilus_trader.adapters.binance.factories import BinanceLiveDataClientFactory
from nautilus_trader.adapters.binance.factories import BinanceLiveExecClientFactory
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.live.node import TradingNode


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


def get_binance_account_type(account_type_str: str) -> BinanceAccountType:
    """
    Convert account type string to BinanceAccountType enum.

    Parameters
    ----------
    account_type_str : str
        The account type string from environment variable.

    Returns
    -------
    BinanceAccountType
        The corresponding BinanceAccountType enum value.
    """
    account_type_map = {
        "spot": BinanceAccountType.SPOT,
        "margin": BinanceAccountType.MARGIN,
        "usdt_future": BinanceAccountType.USDT_FUTURE,
        "coin_future": BinanceAccountType.COIN_FUTURE,
    }

    if account_type_str.lower() not in account_type_map:
        logger.warning(
            f"Invalid account type: {account_type_str}. "
            f"Using default: spot"
        )
        return BinanceAccountType.SPOT

    return account_type_map[account_type_str.lower()]


def create_default_config(paper_trading: bool = False) -> TradingNodeConfig:
    """
    Create a default configuration for the trading node.

    Parameters
    ----------
    paper_trading : bool, default False
        Whether to configure for paper trading.

    Returns
    -------
    TradingNodeConfig
        The default trading node configuration.
    """
    # Get API credentials from environment variables
    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        logger.warning(
            "Binance API credentials not found in environment variables. "
            "Please set BINANCE_API_KEY and BINANCE_API_SECRET."
        )

    # Get account type from environment variable
    account_type_str = os.environ.get("BINANCE_ACCOUNT_TYPE", "spot")
    account_type = get_binance_account_type(account_type_str)

    # Get testnet setting from environment variable
    testnet = os.environ.get("BINANCE_TESTNET", "false").lower() == "true"

    # Get Binance US setting from environment variable
    binance_us = os.environ.get("BINANCE_US", "false").lower() == "true"

    # Get custom endpoints from environment variables
    base_url_http = os.environ.get("BINANCE_BASE_URL_HTTP")
    base_url_ws = os.environ.get("BINANCE_BASE_URL_WS")

    # Configure for paper trading if requested
    if paper_trading:
        logger.info("Configuring for paper trading mode")
        testnet = True

    # Create the trading node configuration
    config = TradingNodeConfig(
        trader_id="BINANCE-TRADER-001",
        logging=LoggingConfig(
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        ),
        data_clients={
            "BINANCE": {
                "api_key": api_key,
                "api_secret": api_secret,
                "account_type": account_type,
                "testnet": testnet,
                "us": binance_us,
                "base_url_http": base_url_http,
                "base_url_ws": base_url_ws,
                "instrument_provider": InstrumentProviderConfig(
                    load_all=True,
                    log_warnings=False,
                ),
            },
        },
        exec_clients={
            "BINANCE": {
                "api_key": api_key,
                "api_secret": api_secret,
                "account_type": account_type,
                "testnet": testnet,
                "us": binance_us,
                "base_url_http": base_url_http,
                "base_url_ws": base_url_ws,
                "instrument_provider": InstrumentProviderConfig(
                    load_all=True,
                    log_warnings=False,
                ),
            },
        },
    )

    return config


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
        logger.info(f"Loading configuration from {config_path}")
        config = TradingNodeConfig.from_yaml(str(config_path))
    else:
        # Use default configuration
        logger.info("Using default configuration")
        config = create_default_config(paper_trading=args.paper)

    try:
        # Initialize the trading node
        node = TradingNode(config=config)

        # Register the Binance client factories
        node.add_data_client_factory("BINANCE", BinanceLiveDataClientFactory)
        node.add_exec_client_factory("BINANCE", BinanceLiveExecClientFactory)

        # Build and run the node
        logger.info("Building and starting the trading node...")
        node.build()
        node.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.exception(f"Error running trading node: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
