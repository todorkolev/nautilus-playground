"""
Spread Capture Module for Market Maker Strategy.

This module contains the core spread capture logic for the market maker strategy.
It handles the creation and management of limit orders on both sides of the market
to capture the bid-ask spread.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from nautilus_trader.model.enums import LiquiditySide, OrderSide
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
        consider_fees: bool = True,
        min_profit_pct: float = 0.0001,  # Minimum profit percentage (0.01%)
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
        consider_fees : bool, optional
            Whether to consider trading fees when calculating order parameters, by default True
        min_profit_pct : float, optional
            Minimum profit percentage required for a trade to be considered profitable, by default 0.0001 (0.01%)

        Returns
        -------
        dict or None
            Dictionary containing order parameters or None if calculation failed
        """
        # Validate inputs early to avoid unnecessary processing
        if mid_price is None or mid_price <= 0:
            return None

        if reference_price is None or reference_price <= 0:
            return None

        if spread is None or spread < 0:
            return None

        if trade_size is None or trade_size <= 0:
            return None

        if self.instrument is None:
            return None

        # Calculate base spread percentage
        market_spread_pct = spread / mid_price if mid_price != 0 else Decimal("0.001")  # Use consistent fallback value

        # Apply spread multiplier - convert all values to Decimal to avoid float precision issues
        min_spread_pct_dec = Decimal(str(min_spread_pct))
        max_spread_pct_dec = Decimal(str(max_spread_pct))
        spread_multiplier_dec = Decimal(str(spread_multiplier))

        # Calculate adjusted spread percentage using pure Decimal arithmetic
        adjusted_spread_pct = market_spread_pct * spread_multiplier_dec

        # Apply min/max constraints
        if adjusted_spread_pct < min_spread_pct_dec:
            base_spread_pct = min_spread_pct_dec
        elif adjusted_spread_pct > max_spread_pct_dec:
            base_spread_pct = max_spread_pct_dec
        else:
            base_spread_pct = adjusted_spread_pct

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

            # Calculate skew factor
            # Use a more adaptive approach that scales with inventory distance
            # As we approach max_inventory, we want to reduce buy size more aggressively
            if inventory_distance > 0:  # We have more than target inventory
                # Scale from 1.0 down to 0.3 as we approach max inventory
                # Using 0.3 as minimum to avoid extremely small order sizes
                inventory_skew_factor = Decimal("1.0") - (inventory_distance * Decimal("0.7"))
                # Ensure we don't go below 0.3 (avoid extremely small buy orders)
                inventory_skew_factor = max(Decimal("0.3"), inventory_skew_factor)
            else:  # We have less than target inventory
                # Scale from 1.0 up to 1.7 as we approach negative max inventory
                inventory_skew_factor = Decimal("1.0") + (abs(inventory_distance) * Decimal("0.7"))
                # Cap at 1.7 to avoid excessive order sizes
                inventory_skew_factor = min(Decimal("1.7"), inventory_skew_factor)

        # Apply ATR adjustment if available
        if atr_value is not None:
            try:
                atr_factor = atr_value / (mid_price * Decimal("0.01")) if mid_price != 0 else Decimal("1.0")

                # Adjust spread based on market regime
                if is_mean_reverting:
                    # Tighter spreads in mean-reverting markets
                    # For mean-reverting markets, we want to reduce the spread
                    adjustment = Decimal("1.0") - atr_factor * Decimal("0.3")
                    # Use built-in max() function instead of .max() method which doesn't exist on Decimal
                    adjustment = max(adjustment, Decimal("0.5"))
                    base_spread_pct = base_spread_pct * adjustment
                else:
                    # Wider spreads in trending markets
                    # For trending markets, we want to increase the spread
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

        # Get minimum allowed size for the instrument
        min_size = self.instrument.size_increment * Decimal("10.0") if self.instrument is not None else Decimal("0.000001")

        # Ensure sizes are either zero or above the minimum allowed size
        if buy_size > Decimal("0") and buy_size < min_size:
            buy_size = min_size
        if sell_size > Decimal("0") and sell_size < min_size:
            sell_size = min_size

        # Apply trend skew (skip sides based on trend detection)
        if skip_buy_side:
            buy_size = Decimal("0")
        if skip_sell_side:
            sell_size = Decimal("0")

        # Check if trades would be profitable after fees
        if consider_fees and self.instrument is not None:
            # Get maker fee for limit orders
            # We use maker fee since we're placing limit orders that should be maker orders
            # This is more accurate than always using the worst-case fee
            fee = self.instrument.maker_fee

            # Calculate minimum required spread to cover fees
            # For a round trip (buy and sell), we need to cover fees on both sides
            min_required_spread_pct = Decimal(str(fee)) * Decimal("2.0") + Decimal(str(min_profit_pct))

            # Calculate actual spread between our bid and ask
            actual_spread_pct = (ask_price - bid_price) / reference_price if reference_price != 0 else Decimal("0")

            # Check if our spread is wide enough to cover fees plus minimum profit
            fee_adjusted = False
            if actual_spread_pct < min_required_spread_pct:
                # Spread is too narrow to be profitable after fees
                # Adjust prices to ensure profitability
                half_adjustment = (min_required_spread_pct - actual_spread_pct) / Decimal("2.0")
                bid_price = bid_price * (Decimal("1.0") - half_adjustment)
                ask_price = ask_price * (Decimal("1.0") + half_adjustment)

                # Verify the adjustment actually made the spread profitable
                new_actual_spread_pct = (ask_price - bid_price) / reference_price if reference_price != 0 else Decimal("0")
                fee_adjusted = new_actual_spread_pct >= min_required_spread_pct
            else:
                # Spread is already wide enough to be profitable
                fee_adjusted = True

        # Return order parameters with accurate fee adjustment status
        return {
            "level": level,
            "bid_price": bid_price,
            "ask_price": ask_price,
            "buy_size": buy_size,
            "sell_size": sell_size,
            "fee_adjusted": consider_fees and fee_adjusted,
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
        already_fee_adjusted : bool, optional
            Whether the price has already been adjusted for fees in compute_order_params, by default False

        Returns
        -------
        LimitOrder or None
            The created order if successful, None otherwise
        """
        if self.instrument is None:
            return None

        # Validate inputs early to avoid unnecessary processing
        # Ensure price is valid
        if price is None or price <= 0:
            return None

        # Skip if size is zero or negative
        if size is None or size <= 0:
            return None

        # Check if size is too small and would be rounded to zero
        if self.instrument is not None:
            min_allowed_size = self.instrument.size_increment
            if size < min_allowed_size:
                # Size is too small for the instrument's precision
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
