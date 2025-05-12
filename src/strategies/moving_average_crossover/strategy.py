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
Implementation of a Moving Average Crossover strategy.
"""

from decimal import Decimal
from typing import Optional, List
from pathlib import Path

import yaml

from nautilus_trader.backtest.node import BacktestDataConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

from src.indicators.pandas_ta_indicator import PandasTaIndicator

class MovingAverageCrossoverConfig(StrategyConfig):
    """
    Configuration for the Moving Average Crossover strategy.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID for the strategy.
    bar_type : BarType
        The bar type for the strategy.
    trade_size : Decimal
        The size for each trade.
    fast_ema_period : int
        The period for the fast EMA.
    slow_ema_period : int
        The period for the slow EMA.
    """

    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast_ema_period: int = 10
    slow_ema_period: int = 20

    @classmethod
    def from_yaml_file(cls, path: str) -> "MovingAverageCrossoverConfig":
        """
        Create a configuration from a YAML file.

        Parameters
        ----------
        path : str
            The path to the YAML file.

        Returns
        -------
        MovingAverageCrossoverConfig
            The configuration.
        """
        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)

        # Extract parameters
        params = config_dict.get("parameters", {})

        # Extract instrument info
        data_config = config_dict.get("data", {})
        instruments = data_config.get("instruments", [])

        if not instruments:
            raise ValueError("No instruments specified in configuration")

        instrument = instruments[0]
        instrument_id = InstrumentId.from_str(instrument["id"])

        # Get bar types
        bar_types = instrument.get("bar_types", [])
        if not bar_types:
            raise ValueError("No bar types specified for instrument")

        # Use the first bar type for the strategy
        bar_type = BarType.from_str(f"{instrument_id.value}-{bar_types[0]}-LAST-EXTERNAL")

        # Create the configuration
        return cls(
            instrument_id=instrument_id,
            bar_type=bar_type,
            trade_size=Decimal(str(params.get("trade_size", 0.1))),
            fast_ema_period=params.get("fast_ema_period", 10),
            slow_ema_period=params.get("slow_ema_period", 20),
        )

    def get_data_configs(self) -> List[BacktestDataConfig]:
        """
        Get the data configurations required for this strategy.

        Returns
        -------
        List[BacktestDataConfig]
            The data configurations.
        """
        # Create data configurations for hourly bars
        return [
            BacktestDataConfig(
                catalog_path="data/catalog",
                data_cls=Bar,
                instrument_id=self.instrument_id,
                bar_spec="1-HOUR",
            ),
        ]


class MovingAverageCrossover(Strategy):
    """
    A Moving Average Crossover strategy.

    This strategy generates buy signals when the fast EMA crosses above the slow EMA,
    and sell signals when the fast EMA crosses below the slow EMA.

    Parameters
    ----------
    config : MovingAverageCrossoverConfig
        The configuration for the strategy.
    """

    def __init__(self, config: MovingAverageCrossoverConfig) -> None:
        super().__init__(config)

        # Configuration
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type
        self.fast_ema_period = config.fast_ema_period
        self.slow_ema_period = config.slow_ema_period
        self.trade_size = config.trade_size

        # Get instrument (may be None during backtesting setup)
        self.instrument = None  # Will be set in on_start

        # Create indicators using PandasTaIndicator
        from nautilus_trader.model.enums import PriceType

        self.fast_ema = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="ema",
            params={"length": self.fast_ema_period},
            price_type=PriceType.LAST,
        )

        self.slow_ema = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="ema",
            params={"length": self.slow_ema_period},
            price_type=PriceType.LAST,
        )

        # Initialize state
        self.previous_fast_ema: Optional[float] = None
        self.previous_slow_ema: Optional[float] = None
        self.position_open = False
        self.position_side: Optional[OrderSide] = None

    def on_start(self) -> None:
        """
        Actions to be performed when the strategy is started.
        """
        self._log.info(f"Strategy {self.id} started")

        # Check if instrument is in cache
        if self.instrument is None:
            self.instrument = self.cache.instrument(self.instrument_id)
            if self.instrument is None:
                self._log.warning(f"Instrument {self.instrument_id} still not found in cache")
                from nautilus_trader.test_kit.providers import TestInstrumentProvider
                self.instrument = TestInstrumentProvider.btcusdt_binance()
                self._log.info(f"Created dummy instrument {self.instrument_id} for backtesting")

        # Subscribe to bars
        self.subscribe_bars(self.bar_type)

    def on_stop(self) -> None:
        """
        Actions to be performed when the strategy is stopped.
        """
        self._log.info(f"Strategy {self.id} stopped")

    def on_reset(self) -> None:
        """
        Actions to be performed when the strategy is reset.
        """
        self._log.info(f"Strategy {self.id} reset")

        # Reset indicators
        self.fast_ema.reset()
        self.slow_ema.reset()

        # Reset state
        self.previous_fast_ema = None
        self.previous_slow_ema = None
        self.position_open = False
        self.position_side = None

    def on_save(self) -> dict:
        """
        Save the strategy state.

        Returns
        -------
        dict
            The strategy state.
        """
        return {
            "previous_fast_ema": self.previous_fast_ema,
            "previous_slow_ema": self.previous_slow_ema,
            "position_open": self.position_open,
            "position_side": self.position_side.name if self.position_side else None,
        }

    def on_load(self, state: dict) -> None:
        """
        Load the strategy state.

        Parameters
        ----------
        state : dict
            The strategy state.
        """
        self.previous_fast_ema = state.get("previous_fast_ema")
        self.previous_slow_ema = state.get("previous_slow_ema")
        self.position_open = state.get("position_open", False)

        position_side = state.get("position_side")
        self.position_side = OrderSide[position_side] if position_side else None

    def on_event(self, event: Event) -> None:
        """
        Actions to be performed when an event is received.

        Parameters
        ----------
        event : Event
            The event received.
        """
        if isinstance(event, OrderFilled):
            self._log.info(f"Order filled: {event.client_order_id} {event.last_qty} @ {event.last_px}")

    def on_data(self, data: Data) -> None:
        """
        Actions to be performed when data is received.

        Parameters
        ----------
        data : Data
            The data received.
        """
        # Check if the data is a Bar and matches our bar type
        if isinstance(data, Bar) and data.bar_type.string == self.bar_type:
            self.handle_bar(data)

    def handle_bar(self, bar: Bar) -> None:
        """
        Handle a bar update.

        Parameters
        ----------
        bar : Bar
            The bar received.
        """
        # Update indicators
        self.fast_ema.handle_bar(bar)
        self.slow_ema.handle_bar(bar)

        # Check if indicators have values
        if self.fast_ema.value is None or self.slow_ema.value is None:
            return

        # Store current values
        current_fast_ema = self.fast_ema.value
        current_slow_ema = self.slow_ema.value

        # Check for crossover if we have previous values
        if self.previous_fast_ema is not None and self.previous_slow_ema is not None:
            # Check for bullish crossover (fast crosses above slow)
            if (self.previous_fast_ema <= self.previous_slow_ema and
                current_fast_ema > current_slow_ema):
                self._log.info(f"Bullish crossover: Fast EMA {current_fast_ema:.4f} crossed above Slow EMA {current_slow_ema:.4f}")
                self._handle_signal(OrderSide.BUY)

            # Check for bearish crossover (fast crosses below slow)
            elif (self.previous_fast_ema >= self.previous_slow_ema and
                  current_fast_ema < current_slow_ema):
                self._log.info(f"Bearish crossover: Fast EMA {current_fast_ema:.4f} crossed below Slow EMA {current_slow_ema:.4f}")
                self._handle_signal(OrderSide.SELL)

        # Update previous values
        self.previous_fast_ema = current_fast_ema
        self.previous_slow_ema = current_slow_ema

    def _handle_signal(self, signal: OrderSide) -> None:
        """
        Handle a trading signal.

        Parameters
        ----------
        signal : OrderSide
            The signal side.
        """
        # Check if we have an open position
        if self.position_open:
            # If signal is opposite to current position, close position
            if self.position_side != signal:
                self._close_position()
                self._open_position(signal)
        else:
            # No position open, open new position
            self._open_position(signal)

    def _open_position(self, side: OrderSide) -> None:
        """
        Open a new position.

        Parameters
        ----------
        side : OrderSide
            The position side.
        """
        # Create order
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=side,
            quantity=self.instrument.make_qty(self.trade_size),
            time_in_force=TimeInForce.GTC,
        )

        # Submit order
        self.submit_order(order)

        # Update state
        self.position_open = True
        self.position_side = side

        self._log.info(f"Opening {side} position with order {order.client_order_id}")

    def _close_position(self) -> None:
        """
        Close the current position.
        """
        if not self.position_open or self.position_side is None:
            return

        # Determine closing side (opposite of position side)
        close_side = OrderSide.SELL if self.position_side == OrderSide.BUY else OrderSide.BUY

        # Create order
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=close_side,
            quantity=self.instrument.make_qty(self.trade_size),
            time_in_force=TimeInForce.GTC,
        )

        # Submit order
        self.submit_order(order)

        # Update state
        self.position_open = False

        self._log.info(f"Closing {self.position_side} position with {close_side} order {order.client_order_id}")
        self.position_side = None
