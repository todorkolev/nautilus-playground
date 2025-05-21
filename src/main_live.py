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

To run with a specific strategy:
    python src/main_live.py --strategy src/strategies/my_strategy/config.yaml

You can also run multiple strategies at once:
    python src/main_live.py --strategy src/strategies/strategy1/config.yaml src/strategies/strategy2/config.yaml
"""

import argparse
import logging
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import for bar type
from nautilus_trader.model.data import BarType

# Add the current directory to the Python path
sys.path.insert(0, os.getcwd())

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
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.config import ImportableStrategyConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.adapters.binance.config import BinanceDataClientConfig
from nautilus_trader.adapters.binance.config import BinanceExecClientConfig


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
        "--strategy",
        type=str,
        nargs="+",
        default=None,
        help="Path(s) to strategy configuration file(s)",
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


def create_default_config(paper_trading: bool = False, strategy_paths: Optional[List[str]] = None) -> TradingNodeConfig:
    """
    Create a default configuration for the trading node.

    Parameters
    ----------
    paper_trading : bool, default False
        Whether to configure for paper trading.
    strategy_paths : Optional[List[str]], default None
        Paths to strategy configuration files.

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

    # Load strategies if provided
    strategies = []
    if strategy_paths:
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
    else:
        logger.info("No strategy specified, running without strategies")

    # Create Binance client configurations
    data_client_config = BinanceDataClientConfig(
        api_key=api_key,
        api_secret=api_secret,
        account_type=account_type,
        testnet=testnet,
        us=binance_us,
        base_url_http=base_url_http,
        base_url_ws=base_url_ws,
    )

    exec_client_config = BinanceExecClientConfig(
        api_key=api_key,
        api_secret=api_secret,
        account_type=account_type,
        testnet=testnet,
        us=binance_us,
        base_url_http=base_url_http,
        base_url_ws=base_url_ws,
    )

    # Create a minimal configuration dictionary
    config_dict = {
        "trader_id": "BINANCE-TRADER-001",
        "strategies": strategies,  # Use the ImportableStrategyConfig objects directly
        "data_clients": {
            "BINANCE": data_client_config,
        },
        "exec_clients": {
            "BINANCE": exec_client_config,
        },
    }

    # Create the trading node configuration
    config = TradingNodeConfig(**config_dict)

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
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
            config = TradingNodeConfig(**config_dict)
    else:
        # Use default configuration with strategies if provided
        logger.info("Using default configuration")
        config = create_default_config(
            paper_trading=args.paper,
            strategy_paths=args.strategy,
        )

    try:
        # Initialize the trading node
        node = TradingNode(config=config)

        # Register the Binance client factories
        node.add_data_client_factory("BINANCE", BinanceLiveDataClientFactory)
        node.add_exec_client_factory("BINANCE", BinanceLiveExecClientFactory)

        # Build the node
        logger.info("Building the trading node...")
        node.build()

        # Log information about the node's structure
        logger.info(f"Node trader ID: {node.trader_id}")
        logger.info(f"Node instance ID: {node.instance_id}")
        logger.info(f"Data engine registered clients: {list(node.kernel.data_engine._clients.keys())}")

        # Ensure instruments are properly loaded before trading
        logger.info("Ensuring instruments are properly loaded...")

        # Get the data client from the data engine's clients dictionary
        # The LiveDataEngine stores clients in a _clients dictionary keyed by ClientId
        from nautilus_trader.model.identifiers import ClientId

        # Try with the exact client ID first
        binance_client_id = ClientId("BINANCE")
        data_client = node.kernel.data_engine._clients[binance_client_id]

        # Get the instrument provider from the data client
        instrument_provider = data_client._instrument_provider
        logger.info(f"Using instrument provider from data client {binance_client_id}")

        # Initialize the instrument provider to load all instruments
        import asyncio

        # First try to load all instruments
        logger.info("Loading all instruments...")
        try:
            if instrument_provider is not None:
                asyncio.run(instrument_provider.initialize(reload=True))
                logger.info("Successfully initialized instrument provider")
            else:
                logger.error("Instrument provider is None, cannot initialize")
        except Exception as e:
            logger.error(f"Error initializing instrument provider: {e}")
            logger.info("Trying to load instruments directly...")

        # Verify that required instruments are loaded
        # This is particularly important for the BTCUSDT.BINANCE instrument
        from nautilus_trader.model.identifiers import InstrumentId
        btcusdt_id = InstrumentId.from_str("BTCUSDT.BINANCE")

        asyncio.run(instrument_provider.load_async(btcusdt_id))
        instrument = instrument_provider.find(btcusdt_id)
        logger.info(f"Specific load result: {instrument is not None}")

        # Run the node
        logger.info("Starting the trading node...")
        node.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.exception(f"Error running trading node: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
