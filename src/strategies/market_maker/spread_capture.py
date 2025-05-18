"""
Spread Capture Module for Market Maker Strategy.

This module contains the core spread capture logic for the market maker strategy.
It handles the creation and management of limit orders on both sides of the market
to capture the bid-ask spread.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import LimitOrder


class SpreadCapture:
    """
    Core spread capture logic for market maker strategy.

    This class handles the creation of limit orders on both sides of the market
    to capture the bid-ask spread. It supports features such as inventory skew,
    dynamic spread adjustment, and multi-level orders.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID for the strategy.
    instrument : Instrument
        The instrument for the strategy.
    """

    def __init__(
        self,
        instrument_id: InstrumentId,
        instrument: Instrument,
    ) -> None:
        self.instrument_id = instrument_id
        self.instrument = instrument

    def compute_order_params(
        self,
        level: int,
        mid_price: Decimal,
        reference_price: Decimal,
        spread: Decimal,
        trade_size: Decimal,
        current_inventory: Decimal,
        max_inventory: Decimal,
        target_inventory_pct: float,
        inventory_skew_enabled: bool,
        spread_multiplier: float,
        min_spread_pct: float,
        max_spread_pct: float,
        level_spacing_pct: float,
        is_mean_reverting: bool,
        atr_value: Optional[Decimal] = None,
        skip_buy_side: bool = False,
        skip_sell_side: bool = False,
    ) -> Optional[Dict]:
        """
        Compute order parameters for a specific level.

        Parameters
        ----------
        level : int
            The level index (0 for closest to mid price, increasing for further levels)
        mid_price : Decimal
            The current mid price
        reference_price : Decimal
            The reference price for order placement (could be mid price or mean in mean-reverting markets)
        spread : Decimal
            The current market spread
        trade_size : Decimal
            The base trade size
        current_inventory : Decimal
            The current inventory position
        max_inventory : Decimal
            The maximum allowed inventory
        target_inventory_pct : float
            The target inventory as percentage of max_inventory
        inventory_skew_enabled : bool
            Whether to enable inventory skew
        spread_multiplier : float
            Multiplier for the spread
        min_spread_pct : float
            Minimum spread as percentage of price
        max_spread_pct : float
            Maximum spread as percentage of price
        level_spacing_pct : float
            Spacing between levels as percentage of price
        is_mean_reverting : bool
            Whether the market is in a mean-reverting regime
        atr_value : Decimal, optional
            The current ATR value, by default None
        skip_buy_side : bool, optional
            Whether to skip the buy side due to trend detection, by default False
        skip_sell_side : bool, optional
            Whether to skip the sell side due to trend detection, by default False

        Returns
        -------
        dict or None
            Dictionary containing order parameters or None if calculation failed
        """
        if mid_price is None or spread is None or self.instrument is None:
            return None

        # Calculate base spread percentage
        market_spread_pct = spread / mid_price if mid_price != 0 else Decimal("0.0")
        
        # Apply spread multiplier
        base_spread_pct = Decimal(str(max(
            min_spread_pct,
            min(max_spread_pct, float(market_spread_pct) * spread_multiplier)
        )))
        
        # Calculate level offset
        level_offset_pct = Decimal(str(level_spacing_pct * level))
        
        # Calculate inventory skew factor (1.0 = neutral, <1.0 = favor buys, >1.0 = favor sells)
        inventory_skew_factor = Decimal("1.0")
        if inventory_skew_enabled and max_inventory > Decimal("0"):
            # Calculate normalized inventory position (-1.0 to 1.0)
            normalized_inventory = current_inventory / max_inventory
            
            # Apply target inventory adjustment
            target_inventory = Decimal(str(target_inventory_pct)) * max_inventory
            inventory_distance = normalized_inventory - (target_inventory / max_inventory)
            
            # Calculate skew factor (0.5 to 1.5)
            inventory_skew_factor = Decimal("1.0") + inventory_distance
            
            # Clamp to reasonable range
            inventory_skew_factor = max(Decimal("0.5"), min(Decimal("1.5"), inventory_skew_factor))
        
        # Apply ATR adjustment if available
        if atr_value is not None:
            try:
                atr_factor = atr_value / (mid_price * Decimal("0.01")) if mid_price != 0 else Decimal("1.0")
                
                # Adjust spread based on market regime
                if is_mean_reverting:
                    # Tighter spreads in mean-reverting markets
                    base_spread_pct = base_spread_pct * (Decimal("1.0") + atr_factor * Decimal("0.3"))
                else:
                    # Wider spreads in trending markets
                    base_spread_pct = base_spread_pct * (Decimal("1.0") + atr_factor * Decimal("0.7"))
            except (ValueError, TypeError):
                # Handle case where ATR value is NaN or invalid
                pass
        
        # Calculate bid and ask spreads
        bid_spread = base_spread_pct / Decimal("2.0") + level_offset_pct
        ask_spread = base_spread_pct / Decimal("2.0") + level_offset_pct
        
        # Use reference price for price calculation
        bid_price = reference_price * (Decimal("1.0") - bid_spread)
        ask_price = reference_price * (Decimal("1.0") + ask_spread)
        
        # Check for NaN or invalid values
        if bid_price.is_nan() or ask_price.is_nan():
            return None
        
        # Adjust for inventory skew
        buy_size = trade_size * inventory_skew_factor
        sell_size = trade_size * (Decimal("2.0") - inventory_skew_factor)
        
        # Apply trend skew (skip sides based on trend detection)
        if skip_buy_side:
            buy_size = Decimal("0")
        if skip_sell_side:
            sell_size = Decimal("0")
        
        # Return order parameters
        return {
            "level": level,
            "bid_price": bid_price,
            "ask_price": ask_price,
            "buy_size": buy_size,
            "sell_size": sell_size,
        }

    def create_limit_order(
        self,
        order_factory,
        side: OrderSide,
        price: Decimal,
        size: Decimal,
        time_in_force,
        expire_time=None,
        post_only=False,
    ) -> Optional[LimitOrder]:
        """
        Create a limit order with the given parameters.

        Parameters
        ----------
        order_factory : OrderFactory
            The order factory to use for creating orders
        side : OrderSide
            The order side (BUY or SELL)
        price : Decimal
            The order price
        size : Decimal
            The order size
        time_in_force : TimeInForce
            The time in force for the order
        expire_time : datetime, optional
            The expiry time for the order, by default None
        post_only : bool, optional
            Whether the order should be post-only, by default False

        Returns
        -------
        LimitOrder or None
            The created order if successful, None otherwise
        """
        if self.instrument is None:
            return None

        # Ensure price is valid
        if price <= 0:
            return None
            
        # Skip if size is zero
        if size <= 0:
            return None

        # Create the order
        order = order_factory.limit(
            instrument_id=self.instrument_id,
            order_side=side,
            quantity=self.instrument.make_qty(size),
            price=self.instrument.make_price(price),
            time_in_force=time_in_force,
            expire_time=expire_time,
            post_only=post_only,
        )
        
        return order
