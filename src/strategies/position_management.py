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
Position management classes for trading strategies.
"""

from enum import Enum
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import ClientOrderId as OrderId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.trading.strategy import Strategy


class Side(Enum):
    """
    Position side enumeration.
    """
    LONG = "LONG"
    SHORT = "SHORT"


class Position:
    """
    Base position class for managing entry and exit orders.

    Parameters
    ----------
    strategy : Strategy
        The strategy managing this position.
    instrument_id : InstrumentId
        The instrument ID for the position.
    side : Side
        The position side (LONG or SHORT).
    quantity : Decimal
        The position quantity.
    entry_price : Optional[float]
        The target entry price (for limit orders).
    take_profit_price : Optional[float]
        The take profit price.
    stop_loss_price : Optional[float]
        The stop loss price.
    position_type : str
        The position type (e.g., "grid", "trend").
    """

    def __init__(
        self,
        strategy: Strategy,
        instrument_id: InstrumentId,
        side: Side,
        quantity: Decimal,
        entry_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        position_type: str = "default",
    ):
        self.strategy = strategy
        self.instrument_id = instrument_id
        self.side = side
        self.quantity = quantity
        self.position_type = position_type

        self._entry_price = entry_price
        self._take_profit_price = take_profit_price
        self._stop_loss_price = stop_loss_price

        self._entry_time: Optional[datetime] = None
        self._filled_quantity: Decimal = Decimal("0")
        self._opened: bool = False

        self._initial_order_id: Optional[OrderId] = None
        self._take_profit_order_id: Optional[OrderId] = None
        self._stop_loss_order_id: Optional[OrderId] = None

        self._current_time: Optional[datetime] = None
        self._current_bar: Optional[Bar] = None
        self._is_stationary: bool = False

        # Get the instrument from the cache
        self.instrument = self.strategy.cache.instrument(self.instrument_id)

        # Place the initial order
        self._place_initial_order()

    def handle_order_event(self, event: OrderFilled) -> None:
        """
        Handle an order filled event.

        Parameters
        ----------
        event : OrderFilled
            The order filled event.
        """
        if event.client_order_id == self._initial_order_id:
            self._opened = True
            self._entry_price = event.last_px
            self._entry_time = datetime.fromtimestamp(event.ts_event / 1_000_000_000)
            self._filled_quantity = event.last_qty

            self._place_take_profit_order()
            self._place_stop_loss_order()

            self.strategy._log.info(
                f"Opened {self.side.value} {self.position_type} position for {self.instrument_id}: "
                f"Quantity: {self._filled_quantity}, Entry Price = {self._entry_price}, "
                f"Entry Time = {self._entry_time}"
            )
        elif (self._take_profit_order_id is not None and event.client_order_id == self._take_profit_order_id) or \
             (self._stop_loss_order_id is not None and event.client_order_id == self._stop_loss_order_id):
            self._opened = False
            self._cancel_remaining_orders()

            exit_price = event.last_px
            profit = (exit_price - self._entry_price) if self.side == Side.LONG else (self._entry_price - exit_price)

            self.strategy._log.info(
                f"Closed {self.side.value} {self.position_type} position for {self.instrument_id}: "
                f"Profit = {profit}, Quantity: {event.last_qty}, "
                f"Entry Price = {self._entry_price}, Entry Time = {self._entry_time}, "
                f"Exit Price = {exit_price}, Exit Time = {datetime.fromtimestamp(event.ts_event / 1_000_000_000)}, "
                f"OrderId: {event.client_order_id}"
            )

    def update(self, bar: Bar) -> None:
        """
        Update the position with the latest bar.

        Parameters
        ----------
        bar : Bar
            The latest bar.
        """
        self._current_time = datetime.fromtimestamp(bar.ts_event / 1_000_000_000)
        self._current_bar = bar

    def market_open(self) -> None:
        """
        Open the position with a market order.
        """
        if self._initial_order_id is not None:
            # Cancel any existing entry order
            # Get the order object from the cache first
            order = self.strategy.cache.order(self._initial_order_id)
            if order is not None:
                self.strategy.cancel_order(order)
            self._initial_order_id = None

        # Create a market order
        order_side = OrderSide.BUY if self.side == Side.LONG else OrderSide.SELL
        order = self.strategy.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=order_side,
            quantity=self.instrument.make_qty(self.quantity),
            time_in_force=TimeInForce.GTC,
        )

        # Submit the order
        self.strategy.submit_order(order)
        self._initial_order_id = order.client_order_id

        # Update state
        self._opened = True
        # We'll get the actual entry price from the order fill event
        self._entry_time = self._current_time
        # Set filled quantity for now (will be updated in handle_order_event)
        self._filled_quantity = self.quantity

        self.strategy._log.info(f"Market order placed. Waiting for fill.")

        # Wait for the order to be filled before placing take profit and stop loss orders
        # The handle_order_event method will place these orders when the order is filled

    def market_close(self) -> None:
        """
        Close the position with a market order.
        """
        if self._opened:
            # Create a market order to close the position
            order_side = OrderSide.SELL if self.side == Side.LONG else OrderSide.BUY
            order = self.strategy.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=order_side,
                quantity=self.instrument.make_qty(self._filled_quantity),
                time_in_force=TimeInForce.GTC,
            )

            # Submit the order
            self.strategy.submit_order(order)

            # Get current price from the latest bar if available
            current_price = "unknown"
            if self._current_bar is not None:
                current_price = self._current_bar.close.as_double()

            self.strategy._log.info(f"Market order closed at approximately {current_price}")

            # Update state
            self._opened = False
            self._cancel_remaining_orders()

    def _place_initial_order(self) -> None:
        """
        Place the initial entry order.
        """
        if self._entry_price is not None:
            # Create a limit order
            order_side = OrderSide.BUY if self.side == Side.LONG else OrderSide.SELL

            # Round the price to the instrument's price precision
            rounded_price = round(self._entry_price, self.instrument.price_precision)

            order = self.strategy.order_factory.limit(
                instrument_id=self.instrument_id,
                order_side=order_side,
                quantity=self.instrument.make_qty(self.quantity),
                price=Price.from_str(str(rounded_price)),
                time_in_force=TimeInForce.GTC,
            )

            # Submit the order
            self.strategy.submit_order(order)
            self._initial_order_id = order.client_order_id

            self.strategy._log.info(
                f"Placed initial limit order for {self.quantity} units at {rounded_price} "
                f"with ID {self._initial_order_id}"
            )

    def _place_take_profit_order(self) -> None:
        """
        Place a take profit order.
        """
        if self._take_profit_price is not None and self._opened:
            # Create a limit order for take profit
            order_side = OrderSide.SELL if self.side == Side.LONG else OrderSide.BUY

            # Round the price to the instrument's price precision
            rounded_price = round(self._take_profit_price, self.instrument.price_precision)

            order = self.strategy.order_factory.limit(
                instrument_id=self.instrument_id,
                order_side=order_side,
                quantity=self.instrument.make_qty(self._filled_quantity),
                price=Price.from_str(str(rounded_price)),
                time_in_force=TimeInForce.GTC,
            )

            # Submit the order
            self.strategy.submit_order(order)
            self._take_profit_order_id = order.client_order_id

            self.strategy._log.info(
                f"Placed take profit order at {self._take_profit_price} with ID {self._take_profit_order_id}"
            )

    def _place_stop_loss_order(self) -> None:
        """
        Place a stop loss order.
        """
        if self._stop_loss_price is not None and self._opened:
            # Create a stop market order for stop loss
            order_side = OrderSide.SELL if self.side == Side.LONG else OrderSide.BUY

            # Round the price to the instrument's price precision
            rounded_price = round(self._stop_loss_price, self.instrument.price_precision)

            order = self.strategy.order_factory.stop_market(
                instrument_id=self.instrument_id,
                order_side=order_side,
                quantity=self.instrument.make_qty(self._filled_quantity),
                trigger_price=Price.from_str(str(rounded_price)),  # Use trigger_price instead of price
                time_in_force=TimeInForce.GTC,
            )

            # Submit the order
            self.strategy.submit_order(order)
            self._stop_loss_order_id = order.client_order_id

            self.strategy._log.info(
                f"Placed stop loss order at {self._stop_loss_price} with ID {self._stop_loss_order_id}"
            )

    def _cancel_remaining_orders(self) -> None:
        """
        Cancel any remaining orders.
        """
        if self._take_profit_order_id is not None:
            # Get the order object from the cache
            order = self.strategy.cache.order(self._take_profit_order_id)
            if order is not None:
                self.strategy.cancel_order(order)
            self._take_profit_order_id = None

        if self._stop_loss_order_id is not None:
            # Get the order object from the cache
            order = self.strategy.cache.order(self._stop_loss_order_id)
            if order is not None:
                self.strategy.cancel_order(order)
            self._stop_loss_order_id = None

    @property
    def opened(self) -> bool:
        """
        Return whether the position is open.
        """
        return self._opened

    @property
    def entry_time(self) -> Optional[datetime]:
        """
        Return the entry time.
        """
        return self._entry_time

    @property
    def entry_price(self) -> Optional[float]:
        """
        Return the entry price.
        """
        return self._entry_price

    @property
    def target_price(self) -> Optional[float]:
        """
        Return the target entry price.
        """
        return self._entry_price

    @property
    def is_stationary(self) -> bool:
        """
        Return whether the position is based on stationary price action.
        """
        return self._is_stationary

    @is_stationary.setter
    def is_stationary(self, value: bool) -> None:
        """
        Set whether the position is based on stationary price action.
        """
        self._is_stationary = value

    @property
    def pnl(self) -> float:
        """
        Return the current profit and loss.
        """
        if not self._opened or self._entry_price is None:
            return 0.0

        # Get the current price from the latest bar if available
        current_price = None
        if hasattr(self, '_current_bar') and self._current_bar is not None:
            current_price = self._current_bar.close.as_double()

        if current_price is None:
            return 0.0

        if self.side == Side.LONG:
            return (current_price - self._entry_price) * float(self._filled_quantity)
        else:  # Side.SHORT
            return (self._entry_price - current_price) * float(self._filled_quantity)

    @property
    def age(self) -> timedelta:
        """
        Return the age of the position.
        """
        if self._opened and self._entry_time is not None and self._current_time is not None:
            return self._current_time - self._entry_time
        else:
            return timedelta(0)


class TrailingStopPosition(Position):
    """
    A position with a trailing stop loss.

    Parameters
    ----------
    strategy : Strategy
        The strategy managing this position.
    instrument_id : InstrumentId
        The instrument ID for the position.
    side : Side
        The position side (LONG or SHORT).
    quantity : Decimal
        The position quantity.
    entry_price : Optional[float]
        The target entry price (for limit orders).
    take_profit_price : Optional[float]
        The take profit price.
    stop_loss_percentage : float
        The stop loss percentage.
    """

    def __init__(
        self,
        strategy: Strategy,
        instrument_id: InstrumentId,
        side: Side,
        quantity: Decimal,
        entry_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        stop_loss_percentage: float = 0.01,
    ):
        self.side_multiplier = 1 if side == Side.LONG else -1
        self.stop_loss_percentage = stop_loss_percentage

        # Calculate initial stop loss price
        stop_loss_price = None
        if entry_price is not None:
            stop_loss_price = entry_price * (1 - self.side_multiplier * stop_loss_percentage)

        super().__init__(
            strategy=strategy,
            instrument_id=instrument_id,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            take_profit_price=take_profit_price,
            stop_loss_price=stop_loss_price,
            position_type="trend",
        )

    def update(self, bar: Bar) -> None:
        """
        Update the position with the latest bar.

        Parameters
        ----------
        bar : Bar
            The latest bar.
        """
        super().update(bar)

        if self._opened:
            # Calculate new stop loss price based on current price
            current_price = bar.close.as_double()
            new_stop_loss_price = current_price * (1 - self.side_multiplier * self.stop_loss_percentage)

            # Update stop loss if it's more favorable
            if self.side == Side.LONG:
                if self._stop_loss_price is None or new_stop_loss_price > self._stop_loss_price:
                    self._update_stop_loss(new_stop_loss_price)
            else:  # Side.SHORT
                if self._stop_loss_price is None or new_stop_loss_price < self._stop_loss_price:
                    self._update_stop_loss(new_stop_loss_price)

    def _update_stop_loss(self, new_price: float) -> None:
        """
        Update the stop loss price.

        Parameters
        ----------
        new_price : float
            The new stop loss price.
        """
        if self._stop_loss_price == new_price:
            return

        self._stop_loss_price = new_price

        # Cancel existing stop loss order
        if self._stop_loss_order_id is not None:
            self.strategy.cancel_order(self._stop_loss_order_id)
            self._stop_loss_order_id = None

        # Place new stop loss order
        self._place_stop_loss_order()


class ShrinkingRangePosition(Position):
    """
    A position with shrinking take profit and stop loss ranges.

    Parameters
    ----------
    strategy : Strategy
        The strategy managing this position.
    instrument_id : InstrumentId
        The instrument ID for the position.
    side : Side
        The position side (LONG or SHORT).
    quantity : Decimal
        The position quantity.
    entry_price : Optional[float]
        The target entry price (for limit orders).
    take_profit_price : Optional[float]
        The take profit price.
    stop_loss_price : Optional[float]
        The stop loss price.
    take_profit_hold : float
        The time to hold the take profit price (in minutes).
    take_profit_decay : float
        The time to decay the take profit price (in minutes).
    stop_loss_hold : float
        The time to hold the stop loss price (in minutes).
    stop_loss_decay : float
        The time to decay the stop loss price (in minutes).
    """

    def __init__(
        self,
        strategy: Strategy,
        instrument_id: InstrumentId,
        side: Side,
        quantity: Decimal,
        entry_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_hold: float = 60.0,
        take_profit_decay: float = 120.0,
        stop_loss_hold: float = 30.0,
        stop_loss_decay: float = 90.0,
    ):
        self.take_profit_hold = take_profit_hold
        self.take_profit_decay = take_profit_decay
        self.stop_loss_hold = stop_loss_hold
        self.stop_loss_decay = stop_loss_decay
        self.initial_take_profit_price = take_profit_price
        self.initial_stop_loss_price = stop_loss_price

        super().__init__(
            strategy=strategy,
            instrument_id=instrument_id,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            take_profit_price=take_profit_price,
            stop_loss_price=stop_loss_price,
            position_type="grid",
        )

    def update(self, bar: Bar) -> None:
        """
        Update the position with the latest bar.

        Parameters
        ----------
        bar : Bar
            The latest bar.
        """
        super().update(bar)

        if self._opened:
            current_price = bar.close.as_double()
            position_age_minutes = self.age.total_seconds() / 60.0

            # Update take profit price
            if self.initial_take_profit_price is not None and position_age_minutes > self.take_profit_hold:
                decay_period = position_age_minutes - self.take_profit_hold
                decay_ratio = min(1.0, decay_period / self.take_profit_decay)
                new_take_profit = current_price + (1 - decay_ratio) * (self.initial_take_profit_price - current_price)
                self._update_take_profit(new_take_profit)

            # Update stop loss price
            if self.initial_stop_loss_price is not None and position_age_minutes > self.stop_loss_hold:
                decay_period = position_age_minutes - self.stop_loss_hold
                decay_ratio = min(1.0, decay_period / self.stop_loss_decay)
                new_stop_loss = current_price + (1 - decay_ratio) * (self.initial_stop_loss_price - current_price)
                self._update_stop_loss(new_stop_loss)

    def _update_take_profit(self, new_price: float) -> None:
        """
        Update the take profit price.

        Parameters
        ----------
        new_price : float
            The new take profit price.
        """
        if self._take_profit_price == new_price:
            return

        self._take_profit_price = new_price

        # Cancel existing take profit order
        if self._take_profit_order_id is not None:
            # Get the order object from the cache
            order = self.strategy.cache.order(self._take_profit_order_id)
            if order is not None:
                self.strategy.cancel_order(order)
            self._take_profit_order_id = None

        # Place new take profit order
        self._place_take_profit_order()

    def _update_stop_loss(self, new_price: float) -> None:
        """
        Update the stop loss price.

        Parameters
        ----------
        new_price : float
            The new stop loss price.
        """
        if self._stop_loss_price == new_price:
            return

        self._stop_loss_price = new_price

        # Cancel existing stop loss order
        if self._stop_loss_order_id is not None:
            # Get the order object from the cache
            order = self.strategy.cache.order(self._stop_loss_order_id)
            if order is not None:
                self.strategy.cancel_order(order)
            self._stop_loss_order_id = None

        # Place new stop loss order
        self._place_stop_loss_order()
