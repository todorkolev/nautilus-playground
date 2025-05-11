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

from decimal import Decimal
from typing import Optional

from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy

from src.indicators.pandas_ta_indicators import PandasTaIndicator
from src.indicators.talib_indicators import TalibIndicator


class IndicatorComparisonConfig(StrategyConfig):
    """
    Configuration for the IndicatorComparison strategy.
    """
    instrument_id: str
    bar_type: str
    rsi_period: int = 14
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    fast_ma_period: int = 10
    slow_ma_period: int = 20
    trade_size: Decimal = Decimal("0.01")


class IndicatorComparisonStrategy(Strategy):
    """
    A strategy that compares indicators from pandas-ta and ta-lib libraries.

    This strategy uses RSI and Moving Average indicators from both libraries
    to generate trading signals. It demonstrates how to use both implementations
    and compares their outputs.

    Parameters
    ----------
    config : IndicatorComparisonConfig
        The strategy configuration.
    """

    def __init__(self, config: IndicatorComparisonConfig):
        super().__init__(config)

        # Configuration
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.bar_type = BarType.from_str(config.bar_type)
        self.rsi_period = config.rsi_period
        self.rsi_oversold = config.rsi_oversold
        self.rsi_overbought = config.rsi_overbought
        self.fast_ma_period = config.fast_ma_period
        self.slow_ma_period = config.slow_ma_period
        self.trade_size = config.trade_size

        # Create indicators
        # pandas-ta indicators
        self.pandas_ta_rsi = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name='rsi',
            params={"length": self.rsi_period},
        )

        self.pandas_ta_fast_ma = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name='ema',
            params={"length": self.fast_ma_period},
        )

        self.pandas_ta_slow_ma = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name='ema',
            params={"length": self.slow_ma_period},
        )

        # ta-lib indicators
        self.talib_rsi = TalibIndicator(
            bar_type=self.bar_type,
            indicator_name='RSI',
            params={"timeperiod": self.rsi_period},
        )

        self.talib_fast_ma = TalibIndicator(
            bar_type=self.bar_type,
            indicator_name='MA',
            params={"timeperiod": self.fast_ma_period, "matype": 1},  # 1 = EMA
        )

        self.talib_slow_ma = TalibIndicator(
            bar_type=self.bar_type,
            indicator_name='MA',
            params={"timeperiod": self.slow_ma_period, "matype": 1},  # 1 = EMA
        )

        # Register indicators
        self.register_indicator_for_bars(self.bar_type, self.pandas_ta_rsi)
        self.register_indicator_for_bars(self.bar_type, self.pandas_ta_fast_ma)
        self.register_indicator_for_bars(self.bar_type, self.pandas_ta_slow_ma)
        self.register_indicator_for_bars(self.bar_type, self.talib_rsi)
        self.register_indicator_for_bars(self.bar_type, self.talib_fast_ma)
        self.register_indicator_for_bars(self.bar_type, self.talib_slow_ma)

        # Strategy state
        self.position_open = False
        self.position_side = None

        # Previous values for crossover detection
        self.previous_pandas_ta_fast_ma = None
        self.previous_pandas_ta_slow_ma = None
        self.previous_talib_fast_ma = None
        self.previous_talib_slow_ma = None

    def on_start(self):
        """
        Actions to be performed when the strategy starts.
        """
        self._log.info("Strategy starting...")

        # Subscribe to bars
        self.subscribe_bars(self.bar_type)

        # Get instrument
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            self._log.error(f"Could not find instrument {self.instrument_id}")
            self.stop()
            return

        self._log.info(f"Strategy started with {self.instrument_id}")

    def on_bar(self, bar: Bar):
        """
        Actions to be performed when a bar is received.

        Parameters
        ----------
        bar : Bar
            The bar received.
        """
        # Check if this is the bar type we're interested in
        if bar.bar_type != self.bar_type:
            return

        # Get indicator values
        pandas_ta_rsi_value = self.pandas_ta_rsi.value
        pandas_ta_fast_ma_value = self.pandas_ta_fast_ma.value
        pandas_ta_slow_ma_value = self.pandas_ta_slow_ma.value

        talib_rsi_value = self.talib_rsi.value
        talib_fast_ma_value = self.talib_fast_ma.value
        talib_slow_ma_value = self.talib_slow_ma.value

        # Log indicator values for comparison
        if (pandas_ta_rsi_value is not None and talib_rsi_value is not None and
            pandas_ta_fast_ma_value is not None and talib_fast_ma_value is not None and
            pandas_ta_slow_ma_value is not None and talib_slow_ma_value is not None):

            self._log.info(f"Bar: {bar.close}")
            self._log.info(f"pandas-ta RSI: {pandas_ta_rsi_value:.2f}, ta-lib RSI: {talib_rsi_value:.2f}, Diff: {abs(pandas_ta_rsi_value - talib_rsi_value):.4f}")
            self._log.info(f"pandas-ta Fast MA: {pandas_ta_fast_ma_value:.4f}, ta-lib Fast MA: {talib_fast_ma_value:.4f}, Diff: {abs(pandas_ta_fast_ma_value - talib_fast_ma_value):.4f}")
            self._log.info(f"pandas-ta Slow MA: {pandas_ta_slow_ma_value:.4f}, ta-lib Slow MA: {talib_slow_ma_value:.4f}, Diff: {abs(pandas_ta_slow_ma_value - talib_slow_ma_value):.4f}")

            # Check for trading signals
            # We'll use the ta-lib indicators for trading decisions
            self._check_ma_crossover(talib_fast_ma_value, talib_slow_ma_value)
            self._check_rsi_signals(talib_rsi_value)

            # Update previous values
            self.previous_pandas_ta_fast_ma = pandas_ta_fast_ma_value
            self.previous_pandas_ta_slow_ma = pandas_ta_slow_ma_value
            self.previous_talib_fast_ma = talib_fast_ma_value
            self.previous_talib_slow_ma = talib_slow_ma_value

    def _check_ma_crossover(self, fast_ma: float, slow_ma: float) -> None:
        """
        Check for moving average crossover signals.

        Parameters
        ----------
        fast_ma : float
            The current fast moving average value.
        slow_ma : float
            The current slow moving average value.
        """
        if self.previous_talib_fast_ma is None or self.previous_talib_slow_ma is None:
            return

        # Check for bullish crossover (fast crosses above slow)
        if (self.previous_talib_fast_ma <= self.previous_talib_slow_ma and
            fast_ma > slow_ma):
            self._log.info(f"Bullish crossover: Fast MA {fast_ma:.4f} crossed above Slow MA {slow_ma:.4f}")
            self._handle_signal(OrderSide.BUY)

        # Check for bearish crossover (fast crosses below slow)
        elif (self.previous_talib_fast_ma >= self.previous_talib_slow_ma and
              fast_ma < slow_ma):
            self._log.info(f"Bearish crossover: Fast MA {fast_ma:.4f} crossed below Slow MA {slow_ma:.4f}")
            self._handle_signal(OrderSide.SELL)

    def _check_rsi_signals(self, rsi: float) -> None:
        """
        Check for RSI signals.

        Parameters
        ----------
        rsi : float
            The current RSI value.
        """
        # Check for oversold condition (RSI below oversold threshold)
        if rsi <= self.rsi_oversold:
            self._log.info(f"RSI oversold: {rsi:.2f}")
            if not self.position_open or self.position_side == OrderSide.SELL:
                self._handle_signal(OrderSide.BUY)

        # Check for overbought condition (RSI above overbought threshold)
        elif rsi >= self.rsi_overbought:
            self._log.info(f"RSI overbought: {rsi:.2f}")
            if not self.position_open or self.position_side == OrderSide.BUY:
                self._handle_signal(OrderSide.SELL)

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
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=side,
            quantity=Quantity.from_str(f"{self.trade_size:.6f}"),
            time_in_force=TimeInForce.GTC,
        )

        self.submit_order(order)
        self._log.info(f"Submitted {side} order {order.client_order_id}")

        self.position_open = True
        self.position_side = side

    def _close_position(self) -> None:
        """
        Close the current position.
        """
        # Determine the closing side (opposite of current position)
        close_side = OrderSide.BUY if self.position_side == OrderSide.SELL else OrderSide.SELL

        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=close_side,
            quantity=Quantity.from_str(f"{self.trade_size:.6f}"),
            time_in_force=TimeInForce.GTC,
        )

        self.submit_order(order)
        self._log.info(f"Submitted {close_side} order {order.client_order_id} to close position")

        self.position_open = False
        self.position_side = None

    def on_event(self, event: Event):
        """
        Actions to be performed when an event is received.

        Parameters
        ----------
        event : Event
            The event received.
        """
        if isinstance(event, OrderFilled):
            self._log.info(f"Order filled: {event}")

    def on_stop(self):
        """
        Actions to be performed when the strategy stops.
        """
        self._log.info("Strategy stopped.")
