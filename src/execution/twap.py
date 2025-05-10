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
Implementation of a Time-Weighted Average Price (TWAP) execution algorithm.
"""

import logging
from decimal import Decimal
from typing import Optional

from nautilus_trader.common.clock import Clock
from nautilus_trader.common.enums import LogColor
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.execution.algorithm import ExecutionAlgorithm
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import StrategyId
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.model.orders import LimitOrder
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy


logger = logging.getLogger(__name__)


class TWAPConfig:
    """
    Configuration for the TWAP execution algorithm.
    
    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID for the algorithm.
    order_side : OrderSide
        The side for the orders.
    total_quantity : Decimal
        The total quantity to execute.
    num_slices : int
        The number of slices to split the order into.
    time_interval_seconds : int
        The time interval between slices in seconds.
    limit_offset_ticks : Optional[int]
        The offset in ticks for limit orders. If None, market orders will be used.
    """
    
    def __init__(
        self,
        instrument_id: InstrumentId,
        order_side: OrderSide,
        total_quantity: Decimal,
        num_slices: int,
        time_interval_seconds: int,
        limit_offset_ticks: Optional[int] = None,
    ):
        self.instrument_id = instrument_id
        self.order_side = order_side
        self.total_quantity = total_quantity
        self.num_slices = num_slices
        self.time_interval_seconds = time_interval_seconds
        self.limit_offset_ticks = limit_offset_ticks


class TWAP(ExecutionAlgorithm):
    """
    A Time-Weighted Average Price (TWAP) execution algorithm.
    
    This algorithm splits a large order into smaller slices and executes them
    at regular time intervals to minimize market impact.
    
    Parameters
    ----------
    trader_id : TraderId
        The trader ID for the algorithm.
    strategy_id : StrategyId
        The strategy ID for the algorithm.
    config : TWAPConfig
        The configuration for the algorithm.
    """
    
    def __init__(
        self,
        trader_id: TraderId,
        strategy_id: StrategyId,
        config: TWAPConfig,
    ):
        super().__init__(trader_id, strategy_id)
        
        self._instrument_id = config.instrument_id
        self._order_side = config.order_side
        self._total_quantity = config.total_quantity
        self._num_slices = config.num_slices
        self._time_interval_seconds = config.time_interval_seconds
        self._limit_offset_ticks = config.limit_offset_ticks
        
        # Calculate slice quantity
        self._slice_quantity = self._total_quantity / self._num_slices
        
        # Initialize state
        self._slices_executed = 0
        self._quantity_executed = Decimal("0")
        self._active_order_id: Optional[ClientOrderId] = None
        self._is_completed = False
        
        # Get instrument
        self._instrument = self.cache.instrument(self._instrument_id)
        if self._instrument is None:
            raise ValueError(f"Instrument {self._instrument_id} not found in cache")
        
        # Validate configuration
        PyCondition.true(self._num_slices > 0, "num_slices must be positive")
        PyCondition.true(self._time_interval_seconds > 0, "time_interval_seconds must be positive")
        PyCondition.true(self._total_quantity > 0, "total_quantity must be positive")
        
        # Schedule first slice
        self.clock.set_timer(
            name="TWAP_SLICE",
            interval=0,  # Execute immediately
            callback=self._execute_slice,
        )
    
    def on_start(self) -> None:
        """
        Actions to be performed when the algorithm is started.
        """
        self._log.info(
            f"Starting TWAP execution: {self._instrument_id} {self._order_side} "
            f"{self._total_quantity} in {self._num_slices} slices "
            f"every {self._time_interval_seconds}s",
            color=LogColor.BLUE,
        )
    
    def on_stop(self) -> None:
        """
        Actions to be performed when the algorithm is stopped.
        """
        if not self._is_completed:
            self._log.warning(
                f"TWAP execution stopped before completion: "
                f"{self._slices_executed}/{self._num_slices} slices executed",
                color=LogColor.YELLOW,
            )
    
    def on_event(self, event: Event) -> None:
        """
        Actions to be performed when an event is received.
        
        Parameters
        ----------
        event : Event
            The event received.
        """
        if isinstance(event, OrderFilled) and event.client_order_id == self._active_order_id:
            self._quantity_executed += event.last_qty
            self._log.info(
                f"Order filled: {event.client_order_id} {event.last_qty} @ {event.last_px}",
                color=LogColor.GREEN,
            )
            
            # Check if all slices have been executed
            if self._slices_executed >= self._num_slices:
                self._is_completed = True
                self._log.info(
                    f"TWAP execution completed: {self._quantity_executed} executed "
                    f"in {self._slices_executed} slices",
                    color=LogColor.BLUE,
                )
    
    def on_data(self, data: Data) -> None:
        """
        Actions to be performed when data is received.
        
        Parameters
        ----------
        data : Data
            The data received.
        """
        # Not used in this algorithm
        pass
    
    def _execute_slice(self) -> None:
        """
        Execute a single slice of the TWAP order.
        """
        if self._is_completed or self._slices_executed >= self._num_slices:
            return
        
        # Calculate quantity for this slice
        remaining_slices = self._num_slices - self._slices_executed
        remaining_quantity = self._total_quantity - self._quantity_executed
        
        if remaining_slices <= 0 or remaining_quantity <= 0:
            self._is_completed = True
            return
        
        slice_quantity = min(self._slice_quantity, remaining_quantity)
        
        # Create order
        if self._limit_offset_ticks is not None:
            # Use limit order with offset
            quote = self.cache.quote_tick(self._instrument_id)
            if quote is None:
                self._log.warning(
                    f"No quote available for {self._instrument_id}, using market order",
                    color=LogColor.YELLOW,
                )
                self._create_market_order(slice_quantity)
                return
            
            # Calculate limit price based on order side and offset
            if self._order_side == OrderSide.BUY:
                base_price = quote.bid_price
                offset_direction = 1  # Add to bid for buy limit
            else:
                base_price = quote.ask_price
                offset_direction = -1  # Subtract from ask for sell limit
            
            tick_size = self._instrument.price_increment
            offset_amount = tick_size * self._limit_offset_ticks * offset_direction
            limit_price = base_price + offset_amount
            
            self._create_limit_order(slice_quantity, limit_price)
        else:
            # Use market order
            self._create_market_order(slice_quantity)
        
        # Increment slice counter
        self._slices_executed += 1
        
        # Schedule next slice if not the last one
        if self._slices_executed < self._num_slices:
            self.clock.set_timer(
                name="TWAP_SLICE",
                interval=self._time_interval_seconds,
                callback=self._execute_slice,
            )
    
    def _create_market_order(self, quantity: Decimal) -> None:
        """
        Create and submit a market order.
        
        Parameters
        ----------
        quantity : Decimal
            The quantity for the order.
        """
        order = self.order_factory.market(
            instrument_id=self._instrument_id,
            order_side=self._order_side,
            quantity=self._instrument.make_qty(quantity),
            time_in_force=TimeInForce.IOC,
        )
        
        self._active_order_id = order.client_order_id
        self.submit_order(order)
        
        self._log.info(
            f"Submitted market order: {order.client_order_id} {order.side} {order.quantity}",
            color=LogColor.BLUE,
        )
    
    def _create_limit_order(self, quantity: Decimal, price: Price) -> None:
        """
        Create and submit a limit order.
        
        Parameters
        ----------
        quantity : Decimal
            The quantity for the order.
        price : Price
            The limit price for the order.
        """
        order = self.order_factory.limit(
            instrument_id=self._instrument_id,
            order_side=self._order_side,
            quantity=self._instrument.make_qty(quantity),
            price=price,
            time_in_force=TimeInForce.GTC,
        )
        
        self._active_order_id = order.client_order_id
        self.submit_order(order)
        
        self._log.info(
            f"Submitted limit order: {order.client_order_id} {order.side} "
            f"{order.quantity} @ {order.price}",
            color=LogColor.BLUE,
        )
