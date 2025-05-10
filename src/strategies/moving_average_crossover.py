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
from typing import Optional

from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.indicators.average.ema import ExponentialMovingAverage
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy


class MovingAverageCrossoverConfig(StrategyConfig):
    """
    Configuration for the Moving Average Crossover strategy.
    
    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID for the strategy.
    bar_type : BarType
        The bar type for the strategy.
    fast_ema_period : int
        The period for the fast EMA.
    slow_ema_period : int
        The period for the slow EMA.
    trade_size : Decimal
        The size for each trade.
    """
    
    instrument_id: InstrumentId
    bar_type: BarType
    fast_ema_period: int = 10
    slow_ema_period: int = 20
    trade_size: Decimal


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
        
        # Get instrument
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            raise ValueError(f"Instrument {self.instrument_id} not found in cache")
        
        # Create indicators
        self.fast_ema = ExponentialMovingAverage(
            bar_type=self.bar_type,
            period=self.fast_ema_period,
        )
        
        self.slow_ema = ExponentialMovingAverage(
            bar_type=self.bar_type,
            period=self.slow_ema_period,
        )
        
        # Initialize state
        self.previous_fast_ema: Optional[float] = None
        self.previous_slow_ema: Optional[float] = None
        self.position_open = False
        self.position_side: Optional[OrderSide] = None
        
        # Register data handlers
        self.register_data_handler(self.bar_type, self.handle_bar)
    
    def on_start(self) -> None:
        """
        Actions to be performed when the strategy is started.
        """
        self._log.info(f"Strategy {self.id} started")
        
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
        # Handled by registered data handlers
        pass
    
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
