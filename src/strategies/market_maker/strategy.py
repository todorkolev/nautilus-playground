"""
Implementation of a Market Maker strategy.

This strategy places and manages limit orders on both sides of the market
to provide liquidity and profit from the bid-ask spread.
"""

import time
from decimal import Decimal
from typing import Dict, List, Optional, Set
import pandas as pd
from datetime import datetime, timedelta

from nautilus_trader.backtest.node import BacktestDataConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.model.data import Bar, QuoteTick
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce, TriggerType
from nautilus_trader.model.events import OrderFilled, OrderCanceled
from nautilus_trader.model.identifiers import InstrumentId, ClientOrderId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.orders import LimitOrder
from nautilus_trader.trading.strategy import Strategy

from src.indicators.pandas_ta_indicator import PandasTaIndicator


class MarketMakerConfig(StrategyConfig):
    """
    Configuration for the Market Maker strategy.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID for the strategy.
    bar_type : BarType
        The bar type for the strategy.
    trade_size : Decimal
        The size for each order.
    max_inventory : Decimal
        The maximum inventory size allowed.
    spread_multiplier : float
        Multiplier for the spread (1.0 = use market spread).
    min_spread_pct : float
        Minimum spread as percentage of price.
    max_spread_pct : float
        Maximum spread as percentage of price.
    order_refresh_seconds : int
        How often to refresh orders in seconds.
    order_levels : int
        Number of order levels on each side.
    level_spacing_pct : float
        Spacing between levels as percentage of price.
    inventory_skew_enabled : bool
        Whether to enable inventory skew.
    target_inventory_pct : float
        Target inventory as percentage of max_inventory.
    time_in_force : str
        Time in force for orders (GTC, GTD, IOC, FOK).
    order_expire_minutes : int
        For GTD orders, how many minutes until expiry.
    post_only : bool
        Whether to use post-only orders.
    """

    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("0.01")
    max_inventory: Decimal = Decimal("0.05")
    spread_multiplier: float = 1.0
    min_spread_pct: float = 0.001
    max_spread_pct: float = 0.01
    order_refresh_seconds: int = 60
    order_levels: int = 1
    level_spacing_pct: float = 0.002
    inventory_skew_enabled: bool = True
    target_inventory_pct: float = 0.0
    time_in_force: str = "GTD"
    order_expire_minutes: int = 5
    post_only: bool = True


class MarketMaker(Strategy):
    """
    A Market Maker strategy.

    This strategy places and manages limit orders on both sides of the market
    to provide liquidity and profit from the bid-ask spread.

    Parameters
    ----------
    config : MarketMakerConfig
        The configuration for the strategy.
    """

    def __init__(self, config: MarketMakerConfig) -> None:
        super().__init__(config)

        # Configuration
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type
        self.trade_size = config.trade_size
        self.max_inventory = config.max_inventory
        self.spread_multiplier = config.spread_multiplier
        self.min_spread_pct = config.min_spread_pct
        self.max_spread_pct = config.max_spread_pct
        self.order_refresh_seconds = config.order_refresh_seconds
        self.order_levels = config.order_levels
        self.level_spacing_pct = config.level_spacing_pct
        self.inventory_skew_enabled = config.inventory_skew_enabled
        self.target_inventory_pct = config.target_inventory_pct
        self.time_in_force = TimeInForce[config.time_in_force]
        self.order_expire_minutes = config.order_expire_minutes
        self.post_only = config.post_only

        # Get instrument (may be None during backtesting setup)
        self.instrument = None  # Will be set in on_start

        # State variables
        self.last_quote: Optional[QuoteTick] = None
        self.current_inventory: Decimal = Decimal("0")
        self.active_buy_orders: Dict[ClientOrderId, LimitOrder] = {}
        self.active_sell_orders: Dict[ClientOrderId, LimitOrder] = {}
        self.last_order_refresh_time: Optional[pd.Timestamp] = None
        self.mid_price: Optional[Decimal] = None
        self.spread: Optional[Decimal] = None

        # Create volatility indicator for dynamic spread adjustment
        self.atr = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="atr",
            params={"length": 14},
        )

        # Register indicators
        self.register_indicator_for_bars(self.bar_type, self.atr)

    def on_start(self) -> None:
        """
        Actions to be performed when the strategy is started.
        """
        self._log.info(f"Strategy {self.id} started")

        # Check if instrument is in cache
        if self.instrument is None:
            self.instrument = self.cache.instrument(self.instrument_id)
            if self.instrument is None:
                self._log.warning(f"Instrument {self.instrument_id} not found in cache")
                from nautilus_trader.test_kit.providers import TestInstrumentProvider
                self.instrument = TestInstrumentProvider.btcusdt_binance()
                self._log.info(f"Created dummy instrument {self.instrument_id} for backtesting")

        # Subscribe to data
        self.subscribe_bars(self.bar_type)
        self.subscribe_quote_ticks(self.instrument_id)

        # Set timer for order refresh
        self.clock.set_timer(
            name="OrderRefresh",
            interval=pd.Timedelta(seconds=self.order_refresh_seconds),
        )

    def on_stop(self) -> None:
        """
        Actions to be performed when the strategy is stopped.
        """
        self._log.info(f"Strategy {self.id} stopped")
        self.cancel_all_orders()

    def on_reset(self) -> None:
        """
        Actions to be performed when the strategy is reset.
        """
        self._log.info(f"Strategy {self.id} reset")
        self.cancel_all_orders()
        self.current_inventory = Decimal("0")
        self.active_buy_orders = {}
        self.active_sell_orders = {}
        self.last_order_refresh_time = None
        self.mid_price = None
        self.spread = None
        self.atr.reset()

    def on_quote_tick(self, tick: QuoteTick) -> None:
        """
        Actions to be performed when a quote tick is received.

        Parameters
        ----------
        tick : QuoteTick
            The quote tick received.
        """
        self.last_quote = tick
        self.update_market_metrics()

    def on_bar(self, bar: Bar) -> None:
        """
        Actions to be performed when a bar is received.

        Parameters
        ----------
        bar : Bar
            The bar received.
        """
        # Update market metrics
        if bar.bar_type == self.bar_type:
            self.update_market_metrics()

    def on_event(self, event: Event) -> None:
        """
        Actions to be performed when an event is received.

        Parameters
        ----------
        event : Event
            The event received.
        """
        if isinstance(event, OrderFilled):
            self.handle_order_filled(event)
        elif isinstance(event, OrderCanceled):
            self.handle_order_canceled(event)

    def on_timer_event(self, event):
        """
        Actions to be performed when a timer event is received.

        Parameters
        ----------
        event : TimerEvent
            The timer event received.
        """
        if event.name == "OrderRefresh":
            self.refresh_orders()

    def update_market_metrics(self) -> None:
        """
        Update market metrics based on the latest data.
        """
        # Try to use quote tick if available
        if self.last_quote is not None:
            # Calculate mid price and spread from quote tick
            bid_price = self.last_quote.bid_price
            ask_price = self.last_quote.ask_price
            self.mid_price = (bid_price + ask_price) / 2
            self.spread = ask_price - bid_price
        else:
            # Fall back to using bar data if quote tick is not available
            last_bar = self.cache.bar(self.bar_type)
            if last_bar is not None:
                # Estimate mid price and spread from bar data
                # For simplicity, we'll use a default spread of 0.1% of the price
                self.mid_price = last_bar.close
                if self.mid_price is not None:
                    self.spread = self.mid_price * Decimal("0.001")
                    self._log.info(f"Using bar data for market metrics: mid={self.mid_price}, spread={self.spread}")
                else:
                    return  # No valid price data
            else:
                return  # No data available

        # Refresh orders if needed
        current_time = self.clock.utc_now()
        if (self.last_order_refresh_time is None or
                (current_time - self.last_order_refresh_time).total_seconds() >= self.order_refresh_seconds):
            self.refresh_orders()
            self.last_order_refresh_time = current_time

    def refresh_orders(self) -> None:
        """
        Refresh all orders based on current market conditions.
        """
        if self.mid_price is None or self.instrument is None or self.spread is None:
            self._log.warning("Cannot refresh orders: missing market data")
            return

        self._log.info(f"Refreshing orders. Mid price: {self.mid_price}, Spread: {self.spread}")

        # Cancel existing orders
        self.cancel_all_orders()

        # Calculate inventory skew if enabled
        inventory_skew_factor = Decimal("1.0")
        if self.inventory_skew_enabled:
            # Calculate current inventory as percentage of max inventory
            current_inventory_pct = self.current_inventory / self.max_inventory if self.max_inventory != 0 else Decimal("0")

            # Calculate skew based on difference from target
            inventory_skew = current_inventory_pct - Decimal(str(self.target_inventory_pct))

            # Apply skew factor (reduce buy size when inventory > target, reduce sell size when inventory < target)
            inventory_skew_factor = Decimal("1.0") - (inventory_skew * Decimal("0.5"))
            inventory_skew_factor = max(min(inventory_skew_factor, Decimal("2.0")), Decimal("0.0"))

            self._log.info(f"Inventory: {self.current_inventory}, Skew factor: {inventory_skew_factor}")

        # Calculate order prices and sizes for each level
        for level in range(self.order_levels):
            # Calculate level offset
            level_offset_pct = Decimal(str(self.level_spacing_pct * level))

            # Calculate relative spread as percentage of price
            relative_spread_pct = self.spread / self.mid_price if self.mid_price != 0 else Decimal("0.001")

            # Calculate base spread percentage with bounds
            base_spread_pct = max(min(Decimal(str(self.spread_multiplier)) * relative_spread_pct,
                                    Decimal(str(self.max_spread_pct))),
                                Decimal(str(self.min_spread_pct)))

            # Apply ATR adjustment if available
            if self.atr.initialized and self.atr.value is not None:
                try:
                    atr_value = Decimal(str(self.atr.value))
                    atr_factor = atr_value / (self.mid_price * Decimal("0.01")) if self.mid_price != 0 else Decimal("1.0")
                    base_spread_pct = base_spread_pct * (Decimal("1.0") + atr_factor * Decimal("0.5"))
                except (ValueError, TypeError):
                    # Handle case where ATR value is NaN or invalid
                    self._log.warning(f"Invalid ATR value: {self.atr.value}, using base spread")

            # Calculate bid and ask prices
            bid_spread = base_spread_pct / Decimal("2.0") + level_offset_pct
            ask_spread = base_spread_pct / Decimal("2.0") + level_offset_pct

            # Ensure prices are valid
            try:
                bid_price = self.mid_price * (Decimal("1.0") - bid_spread)
                ask_price = self.mid_price * (Decimal("1.0") + ask_spread)

                # Check for NaN or invalid values
                if bid_price.is_nan() or ask_price.is_nan():
                    self._log.warning(f"Generated NaN price values, skipping order placement")
                    return
            except Exception as e:
                self._log.error(f"Error calculating prices: {e}")
                return

            # Adjust for inventory skew
            buy_size = self.trade_size * inventory_skew_factor
            sell_size = self.trade_size * (Decimal("2.0") - inventory_skew_factor)

            # Ensure minimum size
            min_size = self.instrument.min_quantity
            buy_size = max(buy_size, min_size)
            sell_size = max(sell_size, min_size)

            # Place orders
            self.place_buy_order(bid_price, buy_size)
            self.place_sell_order(ask_price, sell_size)

    def place_buy_order(self, price: Decimal, size: Decimal) -> None:
        """
        Place a buy limit order.

        Parameters
        ----------
        price : Decimal
            The order price.
        size : Decimal
            The order size.
        """
        if self.instrument is None:
            return

        # Ensure price is valid
        if price <= 0:
            self._log.warning(f"Invalid buy price: {price}, skipping order placement")
            return

        # Ensure size is valid
        if size <= 0:
            self._log.warning(f"Invalid buy size: {size}, skipping order placement")
            return

        # Adjust price to ensure it's not a taker order if post_only is True
        if self.post_only and self.last_quote is not None:
            # If the buy price is higher than or equal to the ask price, it would be a taker order
            if price >= self.last_quote.ask_price:
                # Adjust price to be slightly below the ask price
                price = self.last_quote.ask_price * Decimal("0.9995")
                self._log.info(f"Adjusted BUY price to {price} to avoid taker order")

        # Create the order
        order = self.order_factory.limit(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(size),
            price=self.instrument.make_price(price),
            time_in_force=self.time_in_force,
            expire_time=self.clock.utc_now() + pd.Timedelta(minutes=self.order_expire_minutes) if self.time_in_force == TimeInForce.GTD else None,
            post_only=self.post_only,
        )

        # Submit the order
        self.submit_order(order)
        self.active_buy_orders[order.client_order_id] = order
        self._log.info(f"Placed BUY order: {order.client_order_id} at {price} for {size}")

    def place_sell_order(self, price: Decimal, size: Decimal) -> None:
        """
        Place a sell limit order.

        Parameters
        ----------
        price : Decimal
            The order price.
        size : Decimal
            The order size.
        """
        if self.instrument is None:
            return

        # Ensure price is valid
        if price <= 0:
            self._log.warning(f"Invalid sell price: {price}, skipping order placement")
            return

        # Ensure size is valid
        if size <= 0:
            self._log.warning(f"Invalid sell size: {size}, skipping order placement")
            return

        # Adjust price to ensure it's not a taker order if post_only is True
        if self.post_only and self.last_quote is not None:
            # If the sell price is lower than or equal to the bid price, it would be a taker order
            if price <= self.last_quote.bid_price:
                # Adjust price to be slightly above the bid price
                price = self.last_quote.bid_price * Decimal("1.0005")
                self._log.info(f"Adjusted SELL price to {price} to avoid taker order")

        # Create the order
        order = self.order_factory.limit(
            instrument_id=self.instrument_id,
            order_side=OrderSide.SELL,
            quantity=self.instrument.make_qty(size),
            price=self.instrument.make_price(price),
            time_in_force=self.time_in_force,
            expire_time=self.clock.utc_now() + pd.Timedelta(minutes=self.order_expire_minutes) if self.time_in_force == TimeInForce.GTD else None,
            post_only=self.post_only,
        )

        # Submit the order
        self.submit_order(order)
        self.active_sell_orders[order.client_order_id] = order
        self._log.info(f"Placed SELL order: {order.client_order_id} at {price} for {size}")

    def handle_order_filled(self, event: OrderFilled) -> None:
        """
        Handle an order filled event.

        Parameters
        ----------
        event : OrderFilled
            The order filled event.
        """
        order_id = event.client_order_id
        fill_qty = event.last_qty
        fill_price = event.last_px

        # Update inventory
        if order_id in self.active_buy_orders:
            self.current_inventory += fill_qty
            self._log.info(f"BUY order filled: {order_id} at {fill_price} for {fill_qty}. New inventory: {self.current_inventory}")
            del self.active_buy_orders[order_id]
        elif order_id in self.active_sell_orders:
            self.current_inventory -= fill_qty
            self._log.info(f"SELL order filled: {order_id} at {fill_price} for {fill_qty}. New inventory: {self.current_inventory}")
            del self.active_sell_orders[order_id]

        # Refresh orders after a fill
        self.refresh_orders()

    def handle_order_canceled(self, event: OrderCanceled) -> None:
        """
        Handle an order canceled event.

        Parameters
        ----------
        event : OrderCanceled
            The order canceled event.
        """
        order_id = event.client_order_id

        # Remove from active orders
        if order_id in self.active_buy_orders:
            del self.active_buy_orders[order_id]
            self._log.info(f"BUY order canceled: {order_id}")
        elif order_id in self.active_sell_orders:
            del self.active_sell_orders[order_id]
            self._log.info(f"SELL order canceled: {order_id}")

    def cancel_all_orders(self) -> None:
        """
        Cancel all active orders.
        """
        # Cancel buy orders
        for order_id in list(self.active_buy_orders.keys()):
            self.cancel_order(self.active_buy_orders[order_id])

        # Cancel sell orders
        for order_id in list(self.active_sell_orders.keys()):
            self.cancel_order(self.active_sell_orders[order_id])

        # Clear active orders
        self.active_buy_orders = {}
        self.active_sell_orders = {}
