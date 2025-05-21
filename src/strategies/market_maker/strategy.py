"""
Implementation of an Advanced Market Maker strategy.

This strategy places and manages limit orders on both sides of the market
to provide liquidity and profit from the bid-ask spread. It includes features
such as market regime detection, dynamic spread adjustment, and inventory management.
It also incorporates trend skew, momentum overlay, and risk management features.
"""

import numpy as np
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import pandas as pd

from nautilus_trader.config import StrategyConfig
from nautilus_trader.common.component import TimeEvent
from nautilus_trader.core.message import Event
from nautilus_trader.model.data import Bar, QuoteTick
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce, PositionSide
from nautilus_trader.model.events import OrderFilled, OrderCanceled, PositionChanged, PositionOpened, PositionClosed
from nautilus_trader.model.identifiers import InstrumentId, ClientOrderId, PositionId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.orders import LimitOrder, MarketOrder
from nautilus_trader.model.position import Position
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.currencies import USDT

from src.indicators.pandas_ta_indicator import PandasTaIndicator
from src.strategies.market_maker.spread_capture import SpreadCapture
from src.strategies.market_maker.momentum_overlay import MomentumOverlay
from src.strategies.market_maker.risk_manager import RiskManager


class MarketMakerConfig(StrategyConfig, frozen=True):
    """
    Configuration for the Advanced Market Maker strategy.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID for the strategy.
    bar_type : BarType
        The bar type for the strategy.
    order_levels : int
        Number of order levels on each side. This determines how capital is allocated.
        Capital is divided equally among all order levels.
    spread_multiplier : float
        Multiplier for the spread (1.0 = use market spread).
    min_spread_pct : float
        Minimum spread as percentage of price.
    max_spread_pct : float
        Maximum spread as percentage of price.
    order_refresh_seconds : int
        How often to refresh orders in seconds.
    level_spacing_pct : float
        Spacing between levels as percentage of price.
    inventory_skew_enabled : bool
        Whether to enable inventory skew.
    target_inventory_pct : float
        Target inventory as percentage of max inventory.
    time_in_force : TimeInForce
        Time in force for orders (GTC, GTD, IOC, FOK).
    order_expire_minutes : int
        For GTD orders, how many minutes until expiry.
    post_only : bool
        Whether to use post-only orders.
    enable_mean_reversion : bool
        Whether to enable mean reversion detection and trading.
    atr_period : int
        Period for ATR calculation.
    adx_period : int
        Period for ADX calculation.
    adx_threshold : float
        Threshold for ADX to determine trending vs range-bound market.
    rsi_length : int
        Period for RSI calculation.
    bbands_length : int
        Period for Bollinger Bands calculation.
    bbands_std : float
        Standard deviation multiplier for Bollinger Bands.
    profit_take_pct : float
        Profit taking percentage for accumulated inventory.
    stop_loss_pct : float
        Stop loss percentage for accumulated inventory.
    dynamic_sizing : bool
        Whether to enable dynamic position sizing based on volatility.
    volatility_factor : float
        Factor to adjust order size based on volatility.
    market_regime_check_interval : int
        How often to check market regime in seconds.
    autocorr_threshold : float
        Autocorrelation threshold for mean reversion detection.
    """

    # Required parameters
    instrument_id: InstrumentId
    bar_type: BarType

    # Capital allocation is determined by order_levels
    # trade_size and max_inventory are calculated dynamically

    # Spread capture parameters
    spread_multiplier: float = 1.0
    min_spread_pct: float = 0.001
    max_spread_pct: float = 0.01
    order_refresh_seconds: int = 60
    order_levels: int = 1
    level_spacing_pct: float = 0.002

    # Inventory management
    inventory_skew_enabled: bool = True
    target_inventory_pct: float = 0.0

    # Order execution parameters
    time_in_force: TimeInForce = TimeInForce.GTD
    order_expire_minutes: int = 5
    post_only: bool = True

    # Market regime detection
    enable_mean_reversion: bool = True
    market_regime_check_interval: int = 3600
    autocorr_threshold: float = -0.2

    # Technical indicators
    atr_period: int = 14
    adx_period: int = 14
    adx_threshold: float = 25.0
    rsi_length: int = 14
    bbands_length: int = 20
    bbands_std: float = 2.0

    # Trend skew parameters
    enable_trend_skew: bool = True
    trend_strength_threshold: float = 30.0

    # Momentum overlay parameters
    enable_momentum_overlay: bool = True
    rsi_threshold_high: float = 70.0
    rsi_threshold_low: float = 30.0
    bbands_entry_threshold: float = 2.0
    momentum_trade_size_multiplier: float = 2.0

    # Risk management parameters
    enable_risk_manager: bool = True
    profit_take_pct: float = 0.005
    stop_loss_pct: float = 0.01
    max_drawdown_pct: float = 5.0
    cooldown_minutes: int = 60

    # Dynamic sizing
    dynamic_sizing: bool = False
    volatility_factor: float = 1.0

    # Fee consideration
    consider_fees: bool = True
    min_profit_pct: float = 0.0001  # Minimum profit percentage (0.01%)


class MarketMaker(Strategy):
    """
    An Advanced Market Maker strategy.

    This strategy places and manages limit orders on both sides of the market
    to provide liquidity and profit from the bid-ask spread. It includes features
    such as market regime detection, dynamic spread adjustment, and inventory management.

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

        # Initialize trade_size and max_inventory with default values
        # These will be dynamically calculated based on capital
        self.trade_size = Decimal("0.01")  # Default initial value
        self.max_inventory = Decimal("0.05")  # Default initial value

        # Convert float/int config values to Decimal to avoid repeated conversions
        self._spread_multiplier = Decimal(str(config.spread_multiplier))
        self._min_spread_pct = Decimal(str(config.min_spread_pct))
        self._max_spread_pct = Decimal(str(config.max_spread_pct))
        self._level_spacing_pct = Decimal(str(config.level_spacing_pct))
        self._target_inventory_pct = Decimal(str(config.target_inventory_pct))
        self._profit_take_pct = Decimal(str(config.profit_take_pct))
        self._stop_loss_pct = Decimal(str(config.stop_loss_pct))
        self._volatility_factor = Decimal(str(config.volatility_factor))

        # Keep original values for non-calculation fields
        self.order_refresh_seconds = config.order_refresh_seconds
        self.order_levels = config.order_levels
        self.inventory_skew_enabled = config.inventory_skew_enabled
        self.time_in_force = config.time_in_force  # Already a TimeInForce enum
        self.order_expire_minutes = config.order_expire_minutes
        self.post_only = config.post_only

        # Market regime detection
        self.enable_mean_reversion = config.enable_mean_reversion
        self.market_regime_check_interval = config.market_regime_check_interval
        self._autocorr_threshold = Decimal(str(config.autocorr_threshold))

        # Technical indicators
        self.atr_period = config.atr_period
        self.adx_period = config.adx_period
        self.adx_threshold = config.adx_threshold
        self.rsi_length = config.rsi_length
        self.bbands_length = config.bbands_length
        self.bbands_std = config.bbands_std

        # Trend skew parameters
        self.enable_trend_skew = config.enable_trend_skew
        self.trend_strength_threshold = config.trend_strength_threshold

        # Momentum overlay parameters
        self.enable_momentum_overlay = config.enable_momentum_overlay
        self.rsi_threshold_high = config.rsi_threshold_high
        self.rsi_threshold_low = config.rsi_threshold_low
        self.bbands_entry_threshold = config.bbands_entry_threshold
        self.momentum_trade_size_multiplier = config.momentum_trade_size_multiplier

        # Risk management parameters
        self.enable_risk_manager = config.enable_risk_manager
        self.max_drawdown_pct = config.max_drawdown_pct
        self.cooldown_minutes = config.cooldown_minutes

        # Dynamic sizing
        self.dynamic_sizing = config.dynamic_sizing

        # Set fixed values for capital utilization (always 100%)
        self._capital_utilization_pct = Decimal("1.0")  # 100%

        # Fee consideration
        self.consider_fees = config.consider_fees
        self.min_profit_pct = config.min_profit_pct

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
        self.is_mean_reverting: bool = False
        self.grid_mean: Optional[Decimal] = None
        self.grid_std_dev: Optional[Decimal] = None
        self.last_market_regime_check: Optional[pd.Timestamp] = None

        # Capital utilization state
        self.available_capital: Optional[Decimal] = None
        self.initial_trade_size: Decimal = self.trade_size  # Store original trade size for reference

        # Trend detection state
        self.current_trend: Optional[str] = None  # 'UP', 'DOWN', or None
        self.skip_buy_side: bool = False
        self.skip_sell_side: bool = False

        # Initialize strategy modules
        self.spread_capture: Optional[SpreadCapture] = None  # Will be initialized in on_start
        self.momentum_overlay = MomentumOverlay(
            rsi_threshold_high=self.rsi_threshold_high,
            rsi_threshold_low=self.rsi_threshold_low,
            bbands_entry_threshold=self.bbands_entry_threshold,
            momentum_trade_size_multiplier=self.momentum_trade_size_multiplier,
        )
        self.risk_manager = RiskManager(
            max_drawdown_pct=self.max_drawdown_pct,
            stop_loss_pct=float(self._stop_loss_pct),
            cooldown_minutes=self.cooldown_minutes,
        )

        # Create indicators for market analysis
        self.atr = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="atr",
            params={"length": self.atr_period},
        )

        # ADX for trend strength (includes +DI and -DI)
        self.adx = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="adx",
            params={"length": self.adx_period},
            # Don't specify output_index to ensure all values (ADX, +DI, -DI) are stored in outputs
        )

        # RSI for overbought/oversold conditions
        self.rsi = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="rsi",
            params={"length": self.rsi_length},
        )

        # Bollinger Bands for volatility and mean reversion
        self.bbands = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="bbands",
            params={"length": self.bbands_length, "std": self.bbands_std},
            # Don't specify output_index to ensure all bands are stored in outputs
        )

        # Register indicators
        self.register_indicator_for_bars(self.bar_type, self.atr)
        self.register_indicator_for_bars(self.bar_type, self.adx)
        self.register_indicator_for_bars(self.bar_type, self.rsi)
        self.register_indicator_for_bars(self.bar_type, self.bbands)

    def on_start(self) -> None:
        """
        Actions to be performed when the strategy is started.
        """
        self._log.info(f"Strategy {self.id} started")

        # Check if instrument is in cache
        if self.instrument is None:
            self.instrument = self.cache.instrument(self.instrument_id)
            if self.instrument is None:
                self._log.error(f"Instrument {self.instrument_id} not found in cache")
                self._log.error("Cannot continue without a valid instrument. Stopping strategy.")
                self.stop()
                return

        # Initialize spread capture module
        self.spread_capture = SpreadCapture(
            instrument_id=self.instrument_id,
            instrument=self.instrument,
        )

        # Subscribe to data
        self.subscribe_bars(self.bar_type)
        self.subscribe_quote_ticks(self.instrument_id)

        # Set timer for order refresh
        self.clock.set_timer(
            name="OrderRefresh",
            interval=pd.Timedelta(seconds=self.order_refresh_seconds),
        )

        # Set timer for risk management
        if self.enable_risk_manager:
            self.clock.set_timer(
                name="RiskCheck",
                interval=pd.Timedelta(minutes=1),  # Check risk metrics every minute
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
            # Check if we need to update market regime
            current_time = self.clock.utc_now()
            if (self.enable_mean_reversion and
                (self.last_market_regime_check is None or
                 (current_time - self.last_market_regime_check).total_seconds() >= self.market_regime_check_interval)):
                self.detect_market_regime()
                self.last_market_regime_check = current_time

            self.update_market_metrics()

    def detect_market_regime(self) -> None:
        """
        Detect the current market regime (mean-reverting or trending).
        Uses ADX to determine trend strength and statistical tests for mean reversion.
        Also detects trend direction for trend skew functionality.

        This method analyzes recent price data to determine if the market is in a
        mean-reverting or trending regime. It uses several indicators:
        1. ADX (Average Directional Index) - low values suggest non-trending markets
        2. Autocorrelation of log returns - negative values suggest mean reversion
        3. +DI/-DI for trend direction
        4. RSI for momentum

        When mean reversion is detected, it sets up grid parameters for trading.
        When trending is detected, it sets up trend skew parameters.
        """
        # Early exit if indicators aren't ready
        if not self.adx.initialized or not self.bbands.initialized or not self.rsi.initialized:
            self._log.debug("Cannot detect market regime: indicators not initialized")
            return

        # Get ADX value to determine trend strength
        adx_value = self.adx.value
        if adx_value is None:
            self._log.warning("Cannot detect market regime: ADX value is None")
            return

        # Get recent bars for statistical analysis
        bars = self.cache.bars(self.bar_type)
        if len(bars) < 30:  # Need sufficient data for statistical tests
            self._log.debug(f"Not enough bars for market regime detection: {len(bars)}")
            return

        try:
            # Extract close prices
            prices = np.array([bar.close.as_double() for bar in bars])

            # Check for invalid values
            if np.isnan(prices).any() or np.isinf(prices).any():
                self._log.warning("Invalid price values detected in market regime analysis")
                return

            # Calculate log returns as per user's memory
            log_returns = np.diff(np.log(prices))

            # Check for mean reversion using statistical properties of returns
            # Mean reversion often shows negative autocorrelation in returns
            if len(log_returns) > 1:
                try:
                    autocorr = np.corrcoef(log_returns[:-1], log_returns[1:])[0, 1]

                    # Check if autocorrelation calculation produced a valid result
                    if np.isnan(autocorr):
                        self._log.warning("Autocorrelation calculation resulted in NaN")
                        return

                    # Reset trend flags at the beginning of each regime detection
                    self.skip_buy_side = False
                    self.skip_sell_side = False

                    # Get +DI and -DI values for trend direction regardless of regime
                    plus_di = None
                    minus_di = None
                    using_fallback = False

                    try:
                        # Get DI values from ADX indicator outputs
                        if not self.adx.initialized:
                            self._log.warning("ADX indicator not initialized, using default DI values")
                            plus_di = 20
                            minus_di = 20
                            using_fallback = True
                        else:
                            # Get the outputs dictionary
                            adx_outputs = self.adx.outputs

                            # Log the available keys for debugging
                            self._log.debug(f"ADX outputs keys: {list(adx_outputs.keys())}")

                            # Use the proper pandas-ta ADX column names with period suffix
                            dmp_key = f"DMP_{self.adx_period}"
                            dmn_key = f"DMN_{self.adx_period}"

                            if dmp_key in adx_outputs and dmn_key in adx_outputs:
                                plus_di = adx_outputs[dmp_key]
                                minus_di = adx_outputs[dmn_key]
                                self._log.debug(f"+DI={plus_di:.2f}, -DI={minus_di:.2f}")
                            else:
                                self._log.warning(f"Expected DI keys {dmp_key}/{dmn_key} not found in ADX outputs, using default values")
                                plus_di = 20
                                minus_di = 20
                                using_fallback = True
                    except Exception as e:
                        self._log.warning(f"Error getting directional indicators: {e}")
                        # Safe fallback values
                        plus_di = 20
                        minus_di = 20
                        using_fallback = True

                    # Determine trend direction based on DI values
                    if plus_di > minus_di:
                        trend_direction = 'UP'
                    elif minus_di > plus_di:
                        trend_direction = 'DOWN'
                    else:
                        trend_direction = 'NEUTRAL'

                    # Negative autocorrelation suggests mean reversion
                    is_mean_reverting = (autocorr < float(self._autocorr_threshold) and
                                        adx_value < self.adx_threshold)

                    # Classify market regime based on ADX value
                    if adx_value >= self.trend_strength_threshold:
                        # Strong trend
                        self.current_trend = f"STRONG_{trend_direction}"
                        self.is_mean_reverting = False

                        # Apply trend skew if enabled
                        if self.enable_trend_skew:
                            if trend_direction == 'UP':
                                # In uptrend, reduce sell orders
                                self.skip_sell_side = True
                                self._log.info(f"Detected strong uptrend: ADX={adx_value:.2f}, +DI={plus_di:.2f}, -DI={minus_di:.2f}")
                            elif trend_direction == 'DOWN':
                                # In downtrend, reduce buy orders
                                self.skip_buy_side = True
                                self._log.info(f"Detected strong downtrend: ADX={adx_value:.2f}, +DI={plus_di:.2f}, -DI={minus_di:.2f}")
                    elif adx_value >= self.adx_threshold:
                        # Weak trend (between adx_threshold and trend_strength_threshold)
                        self.current_trend = f"WEAK_{trend_direction}"
                        self.is_mean_reverting = False

                        # Apply mild trend skew for weak trends if enabled
                        if self.enable_trend_skew:
                            # For weak trends, apply a milder version of trend skew
                            if trend_direction == 'UP':
                                # In weak uptrend, slightly reduce sell orders but don't skip
                                self._log.info(f"Detected weak uptrend: ADX={adx_value:.2f}, +DI={plus_di:.2f}, -DI={minus_di:.2f}")
                            elif trend_direction == 'DOWN':
                                # In weak downtrend, slightly reduce buy orders but don't skip
                                self._log.info(f"Detected weak downtrend: ADX={adx_value:.2f}, +DI={plus_di:.2f}, -DI={minus_di:.2f}")
                            else:
                                self._log.info(f"Detected weak neutral trend: ADX={adx_value:.2f}, +DI={plus_di:.2f}, -DI={minus_di:.2f}")
                    else:
                        # Mean-reverting or neutral market
                        if is_mean_reverting:
                            self.current_trend = 'MEAN_REVERTING'
                            self.is_mean_reverting = True

                            # Set grid parameters for mean reversion trading
                            self.grid_mean = Decimal(str(np.mean(prices[-self.bbands_length:])))
                            self.grid_std_dev = Decimal(str(np.std(prices[-self.bbands_length:])))

                            # In mean-reverting markets, don't skip either side
                            self.skip_buy_side = False
                            self.skip_sell_side = False

                            self._log.info(f"Detected mean-reverting market: ADX={adx_value:.2f}, Autocorr={autocorr:.4f}")
                        else:
                            # Low ADX but not mean-reverting - neutral market
                            self.current_trend = 'NEUTRAL'
                            self.is_mean_reverting = False

                            # Ensure flags are explicitly reset for neutral markets
                            self.skip_buy_side = False
                            self.skip_sell_side = False

                            self._log.debug(f"Detected neutral market: ADX={adx_value:.2f}, Autocorr={autocorr:.4f}")

                    # Log if we're using fallback method for DI values
                    if using_fallback:
                        self._log.debug(f"Using fallback trend detection: +DI={plus_di:.2f}, -DI={minus_di:.2f}")

                except (ValueError, IndexError) as e:
                    self._log.warning(f"Error calculating autocorrelation: {e}")

        except Exception as e:
            self._log.error(f"Error in market regime detection: {e}")
            # Don't change the current regime if there's an error

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

    def on_timer_event(self, event: TimeEvent) -> None:
        """
        Actions to be performed when a timer event is received.

        Parameters
        ----------
        event : TimeEvent
            The timer event received.
        """
        if event.name == "OrderRefresh":
            self.refresh_orders()
        elif event.name == "RiskCheck" and self.enable_risk_manager:
            self.check_risk_metrics()

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

    def _calculate_optimal_order_sizes(self) -> None:
        """
        Calculate optimal order sizes based on available capital.

        This method adjusts trade sizes to maximize capital utilization
        in live trading while gracefully falling back to configured sizes
        in backtesting environments.
        """
        # Validate prerequisites
        if self.instrument is None:
            self._log.warning("Cannot calculate optimal order sizes: instrument is None")
            return

        if self.mid_price is None:
            self._log.warning("Cannot calculate optimal order sizes: mid_price is None")
            return

        if self.mid_price <= Decimal("0"):
            self._log.warning(f"Cannot calculate optimal order sizes: invalid mid_price {self.mid_price}")
            return

        # Store original trade size
        original_trade_size = self.trade_size

        try:
            # Get the account for this venue
            venue = self.instrument_id.venue
            account = self.portfolio.account(venue)

            if not account:
                error_msg = f"No account found for venue {venue}"
                self._log.error(error_msg)
                raise ValueError(error_msg)

            # Try to determine the appropriate currency
            currency = USDT

            free_balance = account.balance_free(currency)
            total_capital = free_balance.as_decimal()

            # Store for reference
            self.available_capital = total_capital
            self._log.info(f"Available capital: {total_capital}")


            # Calculate the total number of orders we'll place (order_levels on each side)
            total_orders = self.order_levels * 2  # Buy and sell sides

            # Calculate capital per order by dividing total capital by number of orders
            capital_per_order_pct = Decimal("1.0") / Decimal(str(total_orders))
            self._log.info(f"Capital per order percentage: {capital_per_order_pct * Decimal('100.0')}%")

            # Calculate capital allocated per order
            capital_per_order = total_capital * capital_per_order_pct
            self._log.info(f"Capital per order: {capital_per_order}")

            # Calculate size based on price
            target_size = capital_per_order / self.mid_price
            self._log.info(f"Raw target size: {target_size}")

            # Ensure minimum size
            min_size = self.instrument.size_increment * Decimal("10.0")
            if target_size < min_size:
                self._log.info(f"Target size {target_size} below minimum {min_size}, using minimum")
                target_size = min_size

            # Round to instrument precision
            target_size = (target_size // self.instrument.size_increment) * self.instrument.size_increment
            self._log.info(f"Final target size after rounding: {target_size}")

            # Update trade size if significantly different (>10% change)
            if target_size > Decimal("0") and abs((target_size / self.trade_size) - Decimal("1.0")) > Decimal("0.1"):
                old_size = self.trade_size
                self.trade_size = target_size
                self._log.info(f"Adjusted trade size from {old_size} to {target_size} for optimal capital utilization")
            else:
                self._log.debug(f"Keeping current trade size {self.trade_size} (change not significant)")

        except Exception as e:
            # Revert to original trade size on any error
            self.trade_size = original_trade_size
            error_msg = f"Error calculating optimal order sizes: {e}"
            self._log.error(error_msg)
            # Re-raise the exception to stop order placement
            raise RuntimeError(error_msg) from e

    def _compute_reference_price(self) -> Optional[Decimal]:
        """
        Compute the reference price for order placement based on market regime.

        Returns
        -------
        Decimal or None
            The reference price to use for order placement, or None if it cannot be determined.
        """
        if self.mid_price is None:
            return None

        # Determine reference price based on market regime
        if self.is_mean_reverting and self.grid_mean is not None:
            # In mean reversion mode, use the detected mean as reference
            reference_price = self.grid_mean
            self._log.debug(f"Using mean reversion grid mean: {reference_price}")
        else:
            reference_price = self.mid_price

        return reference_price

    # _compute_order_params method removed to eliminate duplicate logic
    # All order parameter computation is now handled by SpreadCapture.compute_order_params

    def _submit_orders(self, params_list: List[Dict]) -> None:
        """
        Submit orders based on the provided parameters.

        Parameters
        ----------
        params_list : List[Dict]
            List of parameter dictionaries from _compute_order_params
        """
        for params in params_list:
            if params is None:
                continue

            # Check if the parameters were adjusted for fees
            fee_adjusted = params.get("fee_adjusted", False)
            if fee_adjusted:
                self._log.debug(f"Using fee-adjusted prices: bid={params['bid_price']}, ask={params['ask_price']}")

            # Place orders if sizes are greater than zero
            if params["buy_size"] > 0:
                self._place_limit_order(OrderSide.BUY, params["bid_price"], params["buy_size"])

            if params["sell_size"] > 0:
                self._place_limit_order(OrderSide.SELL, params["ask_price"], params["sell_size"])

    def _should_replace_order(self, existing_order, new_price, new_size, price_threshold_pct=0.001):
        """
        Determine if an existing order should be replaced based on price and size differences.

        Parameters
        ----------
        existing_order : LimitOrder
            The existing order
        new_price : Decimal
            The new desired price
        new_size : Decimal
            The new desired size
        price_threshold_pct : float
            The threshold percentage difference in price to trigger replacement

        Returns
        -------
        bool
            True if the order should be replaced, False otherwise
        """
        if existing_order is None:
            return True

        # Calculate price difference as percentage
        price_diff_pct = abs(existing_order.price.as_decimal() - new_price) / existing_order.price.as_decimal()

        # Check if size has changed significantly
        size_changed = abs(existing_order.quantity.as_decimal() - new_size) / existing_order.quantity.as_decimal() > 0.05

        # Replace if price difference exceeds threshold or size has changed significantly
        return price_diff_pct > Decimal(str(price_threshold_pct)) or size_changed

    def _find_closest_order(self, target_price, orders_dict):
        """
        Find the closest existing order to the target price.

        Parameters
        ----------
        target_price : Decimal
            The target price to compare against
        orders_dict : Dict[ClientOrderId, LimitOrder]
            Dictionary of active orders

        Returns
        -------
        LimitOrder or None
            The closest order if found, None otherwise
        """
        closest_order = None
        min_price_diff = Decimal('inf')

        for _, order in orders_dict.items():
            if order.is_closed:
                continue

            price_diff = abs(order.price.as_decimal() - target_price)
            if price_diff < min_price_diff:
                min_price_diff = price_diff
                closest_order = order

        return closest_order

    def _clean_order_dictionaries(self):
        """
        Clean up the order dictionaries by removing closed orders.
        """
        # Remove closed buy orders
        for order_id in list(self.active_buy_orders.keys()):
            order = self.active_buy_orders[order_id]
            if order.is_closed:
                del self.active_buy_orders[order_id]

        # Remove closed sell orders
        for order_id in list(self.active_sell_orders.keys()):
            order = self.active_sell_orders[order_id]
            if order.is_closed:
                del self.active_sell_orders[order_id]

    def refresh_orders(self) -> None:
        """
        Refresh orders intelligently based on current market conditions and market regime.
        Only cancels and replaces orders when necessary.
        """
        if self.mid_price is None or self.instrument is None or self.spread is None:
            self._log.warning("Cannot refresh orders: missing market data")
            return

        # Check if risk manager is in shutdown mode
        if self.enable_risk_manager and self.risk_manager.is_shutdown:
            self._log.info("Risk manager in shutdown mode, not placing orders")
            return

        self._log.info(f"Refreshing orders. Mid price: {self.mid_price}, Spread: {self.spread}")
        self._log.debug(f"Market regime: {'Mean-reverting' if self.is_mean_reverting else 'Trending'}")
        self._log.debug(f"Inventory: {self.current_inventory}")

        if self.current_trend is not None:
            self._log.debug(f"Current trend: {self.current_trend}, Skip buy: {self.skip_buy_side}, Skip sell: {self.skip_sell_side}")

        # Clean up closed orders from our tracking dictionaries
        self._clean_order_dictionaries()

        # Check for momentum overlay signals
        if self.enable_momentum_overlay and not self.momentum_overlay.active_momentum_trade:
            # Get indicator values for momentum detection
            rsi_value = self.rsi.value if self.rsi.initialized and self.rsi.value is not None else 50.0
            bbands_upper = None
            bbands_lower = None
            bbands_middle = None

            # Try to get Bollinger Bands values
            try:
                if self.bbands.initialized:
                    # Get the outputs dictionary
                    bbands_outputs = self.bbands.outputs

                    # Log the available keys for debugging
                    self._log.debug(f"Bollinger Bands outputs keys: {list(bbands_outputs.keys())}")

                    # Check for standard pandas-ta bbands column names
                    if 'BBU' in bbands_outputs and 'BBL' in bbands_outputs and 'BBM' in bbands_outputs:
                        bbands_upper = Decimal(str(bbands_outputs['BBU']))
                        bbands_lower = Decimal(str(bbands_outputs['BBL']))
                        bbands_middle = Decimal(str(bbands_outputs['BBM']))
                        self._log.debug(f"Using BBU/BBL/BBM format: U={bbands_upper}, M={bbands_middle}, L={bbands_lower}")
                    # Check for alternative column names
                    elif 'upper' in bbands_outputs and 'lower' in bbands_outputs and 'middle' in bbands_outputs:
                        bbands_upper = Decimal(str(bbands_outputs['upper']))
                        bbands_lower = Decimal(str(bbands_outputs['lower']))
                        bbands_middle = Decimal(str(bbands_outputs['middle']))
                        self._log.debug(f"Using upper/lower/middle format: U={bbands_upper}, M={bbands_middle}, L={bbands_lower}")
                    # If we can't find the expected keys, try to infer from available keys
                    elif len(bbands_outputs) >= 3:
                        # Get all keys and sort them - typically the upper band has the highest value
                        keys = list(bbands_outputs.keys())
                        values = [bbands_outputs[k] for k in keys]

                        # Sort keys by their values (assuming upper > middle > lower)
                        sorted_keys = [k for _, k in sorted(zip(values, keys), reverse=True)]

                        bbands_upper = Decimal(str(bbands_outputs[sorted_keys[0]]))
                        bbands_middle = Decimal(str(bbands_outputs[sorted_keys[1]]))
                        bbands_lower = Decimal(str(bbands_outputs[sorted_keys[2]]))
                        self._log.debug(f"Inferred bands from keys {sorted_keys}: U={bbands_upper}, M={bbands_middle}, L={bbands_lower}")
            except Exception as e:
                self._log.warning(f"Error getting Bollinger Bands values: {e}")

            # Detect momentum signals
            signal_detected, direction = self.momentum_overlay.detect_momentum(
                rsi_value=float(rsi_value),
                price=self.mid_price,
                bbands_upper=bbands_upper,
                bbands_lower=bbands_lower,
                bbands_middle=bbands_middle,
            )

            if signal_detected and direction is not None:
                # Execute momentum trade
                self._log.info(f"Momentum signal detected: {direction}")

                # Calculate momentum trade size - use current trade_size which is dynamically adjusted
                momentum_size = self.momentum_overlay.calculate_momentum_trade_size(self.trade_size)

                # Adjust momentum size based on available capital if possible
                try:
                    # Use available_capital if we have it from previous calculations
                    if self.available_capital is not None and self.available_capital > Decimal("0"):
                        # For momentum trades, use up to 50% of available capital
                        max_momentum_capital = self.available_capital * Decimal("0.5")

                        # Calculate maximum size based on price
                        if self.mid_price is not None and self.mid_price > Decimal("0"):
                            max_size = max_momentum_capital / self.mid_price

                            # Apply constraints
                            if max_size > self.max_inventory:
                                max_size = self.max_inventory

                            # Limit momentum size if needed
                            if momentum_size > max_size:
                                momentum_size = max_size

                    # Ensure valid size
                    if self.instrument is not None:
                        # Round to instrument precision
                        momentum_size = (momentum_size // self.instrument.size_increment) * self.instrument.size_increment

                        # Ensure minimum size
                        min_size = self.instrument.size_increment * Decimal("10.0")
                        if momentum_size < min_size:
                            momentum_size = min_size
                except Exception as e:
                    self._log.debug(f"Using default momentum size: {e}")

                # Place market order for momentum trade
                if direction == 'LONG':
                    self._log.info(f"Executing momentum LONG trade with size {momentum_size}")
                    # Create and submit market order
                    order = self.order_factory.market(
                        instrument_id=self.instrument_id,
                        order_side=OrderSide.BUY,
                        quantity=self.instrument.make_qty(momentum_size),
                    )
                    self.submit_order(order)

                    # Track the market order in active_buy_orders
                    self.active_buy_orders[order.client_order_id] = order

                    # Update momentum overlay state with current time
                    self.momentum_overlay.start_momentum_trade(
                        direction=direction,
                        entry_price=self.mid_price,
                        entry_time=self.clock.utc_now()
                    )

                elif direction == 'SHORT':
                    self._log.info(f"Executing momentum SHORT trade with size {momentum_size}")
                    # Create and submit market order
                    order = self.order_factory.market(
                        instrument_id=self.instrument_id,
                        order_side=OrderSide.SELL,
                        quantity=self.instrument.make_qty(momentum_size),
                    )
                    self.submit_order(order)

                    # Track the market order in active_sell_orders
                    self.active_sell_orders[order.client_order_id] = order

                    # Update momentum overlay state with current time
                    self.momentum_overlay.start_momentum_trade(
                        direction=direction,
                        entry_price=self.mid_price,
                        entry_time=self.clock.utc_now()
                    )

                # Skip regular order placement when executing momentum trade
                return

        # Check if we have an active momentum trade
        momentum_trade_active = False
        if self.enable_momentum_overlay and self.momentum_overlay.active_momentum_trade:
            # Update momentum trade status
            rsi_value = self.rsi.value if self.rsi.initialized and self.rsi.value is not None else 50.0
            should_exit, is_profit = self.momentum_overlay.update_momentum_trade_status(
                price=self.mid_price,
                rsi_value=float(rsi_value),
                profit_take_pct=float(self._profit_take_pct),
            )

            if should_exit:
                # Close momentum trade
                self._log.info(f"Exiting momentum trade: {'profit target' if is_profit else 'exit signal'}")

                # Close all positions
                positions = self.cache.positions_open(self.instrument_id)
                for position in positions:
                    self.close_position(position)

                # End momentum trade
                self.momentum_overlay.end_momentum_trade()
            else:
                # Momentum trade is still active
                momentum_trade_active = True

                # Check if momentum trade has been active for too long
                current_time = self.clock.utc_now()
                momentum_duration = (current_time - self.momentum_overlay.momentum_entry_time).total_seconds() if self.momentum_overlay.momentum_entry_time else 0

                # If momentum trade has been active for more than 5 minutes, allow regular orders alongside it
                if momentum_duration > 300:  # 5 minutes in seconds
                    self._log.info(f"Momentum trade active for {momentum_duration:.0f} seconds, allowing regular orders alongside")
                    momentum_trade_active = False

            # Only skip regular order placement if momentum trade is still active and not too old
            if momentum_trade_active:
                self._log.debug("Skipping regular order placement due to active momentum trade")
                return

        # Use SpreadCapture module to compute order parameters
        reference_price = self._compute_reference_price()
        if reference_price is None:
            return

        # Ensure SpreadCapture is initialized
        if self.spread_capture is None:
            self.spread_capture = SpreadCapture(
                instrument_id=self.instrument_id,
                instrument=self.instrument,
            )

        # Calculate optimal order sizes based on current capital
        self._calculate_optimal_order_sizes()

        # Compute parameters for each level
        params_list = []
        for level in range(self.order_levels):
            # Use SpreadCapture module with dynamically adjusted trade size
            params = self.spread_capture.compute_order_params(
                level=level,
                mid_price=self.mid_price,
                reference_price=reference_price,
                spread=self.spread,
                trade_size=self.trade_size,
                current_inventory=self.current_inventory,
                max_inventory=self.max_inventory,
                target_inventory_pct=float(self._target_inventory_pct),
                inventory_skew_enabled=self.inventory_skew_enabled,
                spread_multiplier=float(self._spread_multiplier),
                min_spread_pct=float(self._min_spread_pct),
                max_spread_pct=float(self._max_spread_pct),
                level_spacing_pct=float(self._level_spacing_pct),
                is_mean_reverting=self.is_mean_reverting,
                atr_value=Decimal(str(self.atr.value)) if self.atr.initialized and self.atr.value is not None else None,
                skip_buy_side=self.skip_buy_side,
                skip_sell_side=self.skip_sell_side,
                consider_fees=self.consider_fees,
                min_profit_pct=self.min_profit_pct,
            )

            if params is not None:
                params_list.append(params)

        # Smart order management - track which orders to keep
        orders_to_keep = set()

        # Process each parameter set
        for params in params_list:
            # Process buy orders if size > 0
            if params["buy_size"] > 0 and not self.skip_buy_side:
                # Find closest existing buy order
                closest_buy_order = self._find_closest_order(
                    params["bid_price"],
                    self.active_buy_orders
                )

                # Check if we should keep or replace the order
                if closest_buy_order and not self._should_replace_order(
                    closest_buy_order,
                    params["bid_price"],
                    params["buy_size"]
                ):
                    # Keep this order, it's close enough
                    orders_to_keep.add(closest_buy_order.client_order_id)
                    self._log.debug(f"Keeping BUY order {closest_buy_order.client_order_id} at {closest_buy_order.price}")
                else:
                    # Place new order
                    self._place_limit_order(OrderSide.BUY, params["bid_price"], params["buy_size"])

            # Process sell orders if size > 0
            if params["sell_size"] > 0 and not self.skip_sell_side:
                # Find closest existing sell order
                closest_sell_order = self._find_closest_order(
                    params["ask_price"],
                    self.active_sell_orders
                )

                # Check if we should keep or replace the order
                if closest_sell_order and not self._should_replace_order(
                    closest_sell_order,
                    params["ask_price"],
                    params["sell_size"]
                ):
                    # Keep this order, it's close enough
                    orders_to_keep.add(closest_sell_order.client_order_id)
                    self._log.debug(f"Keeping SELL order {closest_sell_order.client_order_id} at {closest_sell_order.price}")
                else:
                    # Place new order
                    self._place_limit_order(OrderSide.SELL, params["ask_price"], params["sell_size"])

        # Cancel orders that weren't kept
        for order_id, order in list(self.active_buy_orders.items()):
            if order_id not in orders_to_keep and not order.is_closed:
                self._log.debug(f"Canceling BUY order {order_id} at {order.price}")
                self.cancel_order(order)

        for order_id, order in list(self.active_sell_orders.items()):
            if order_id not in orders_to_keep and not order.is_closed:
                self._log.debug(f"Canceling SELL order {order_id} at {order.price}")
                self.cancel_order(order)

    def _place_limit_order(self, side: OrderSide, price: Decimal, size: Decimal) -> Optional[LimitOrder]:
        """
        Place a limit order with the given parameters.

        This is a private helper method that handles common validation, price adjustment,
        order creation and tracking for both buy and sell orders.

        Parameters
        ----------
        side : OrderSide
            The order side (BUY or SELL).
        price : Decimal
            The order price.
        size : Decimal
            The order size.

        Returns
        -------
        LimitOrder or None
            The created order if successful, None otherwise.
        """
        if self.instrument is None:
            return None

        # Ensure price is valid
        if price <= 0:
            self._log.warning(f"Invalid {side.name} price: {price}, skipping order placement")
            return None

        # Ensure size is valid
        if size <= 0:
            self._log.warning(f"Invalid {side.name} size: {size}, skipping order placement")
            return None

        # Check if size is too small for the instrument's precision
        if self.instrument is not None:
            min_allowed_size = self.instrument.size_increment * Decimal("10.0")
            if size < min_allowed_size:
                self._log.warning(f"Size {size} is too small for {self.instrument_id}, minimum is {min_allowed_size}")
                return None

        # Adjust price to ensure it's not a taker order if post_only is True
        if self.post_only and self.last_quote is not None:
            # Use instrument tick size for price adjustments if available
            tick_size = self.instrument.price_increment if self.instrument is not None else Decimal("0.0001")

            # Calculate price adjustment factor based on tick size
            # Default to 1 tick away from the current price
            price_adjustment_factor = tick_size

            if side == OrderSide.BUY:
                # If the buy price is higher than or equal to the ask price, it would be a taker order
                if price >= self.last_quote.ask_price:
                    # Adjust price to be below the ask price by at least one tick
                    price = self.last_quote.ask_price - price_adjustment_factor
                    self._log.debug(f"Adjusted BUY price to {price} to avoid taker order")
            else:  # SELL
                # If the sell price is lower than or equal to the bid price, it would be a taker order
                if price <= self.last_quote.bid_price:
                    # Adjust price to be above the bid price by at least one tick
                    price = self.last_quote.bid_price + price_adjustment_factor
                    self._log.debug(f"Adjusted SELL price to {price} to avoid taker order")

        # Create order using SpreadCapture
        # Note: Fee consideration is now handled in compute_order_params, not here
        if self.spread_capture is not None:
            order = self.spread_capture.create_limit_order(
                order_factory=self.order_factory,
                side=side,
                price=price,
                size=size,
                time_in_force=self.time_in_force,
                expire_time=self.clock.utc_now() + pd.Timedelta(minutes=self.order_expire_minutes) if self.time_in_force == TimeInForce.GTD else None,
                post_only=self.post_only,
            )

            # If order creation failed, log and return
            if order is None:
                self._log.info(f"Failed to create {side.name} order at {price} for {size}")
                return None
        else:
            # Create the order without fee consideration
            order = self.order_factory.limit(
                instrument_id=self.instrument_id,
                order_side=side,
                quantity=self.instrument.make_qty(size),
                price=self.instrument.make_price(price),
                time_in_force=self.time_in_force,
                expire_time=self.clock.utc_now() + pd.Timedelta(minutes=self.order_expire_minutes) if self.time_in_force == TimeInForce.GTD else None,
                post_only=self.post_only,
            )

        # Submit the order
        self.submit_order(order)

        # Track the order in the appropriate collection
        if side == OrderSide.BUY:
            self.active_buy_orders[order.client_order_id] = order
        else:
            self.active_sell_orders[order.client_order_id] = order

        self._log.debug(f"Placed {side.name} order: {order.client_order_id} at {price} for {size}")
        return order

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
        self._place_limit_order(OrderSide.BUY, price, size)

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
        self._place_limit_order(OrderSide.SELL, price, size)

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

        # Don't refresh orders immediately after every fill
        # This avoids excessive order churn
        # Orders will be refreshed on the next timer event or market update

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
            self._log.debug(f"BUY order canceled: {order_id}")
        elif order_id in self.active_sell_orders:
            del self.active_sell_orders[order_id]
            self._log.debug(f"SELL order canceled: {order_id}")

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

    def check_risk_metrics(self) -> None:
        """
        Check risk metrics and take appropriate actions.

        This method updates the risk manager with current equity information,
        checks for drawdown conditions, and manages stop-loss for positions.
        """
        if not self.enable_risk_manager:
            return

        # Get current account information
        account = self.portfolio.default_account
        if account is None:
            self._log.warning("Cannot check risk metrics: no account available")
            return

        # Update risk manager with current equity
        try:
            # Get total equity (may need adjustment based on actual implementation)
            equity = account.balance_total()
            if equity is not None:
                self.risk_manager.update_equity(equity.as_decimal())

                # Check if we should shut down due to drawdown
                current_time = self.clock.utc_now()
                if self.risk_manager.check_shutdown_condition(current_time):
                    self._log.warning(f"Risk manager triggered shutdown: drawdown={self.risk_manager.current_drawdown_pct:.2f}%")

                    # Cancel all orders during shutdown
                    self.cancel_all_orders()
                    return
        except Exception as e:
            self._log.error(f"Error updating risk manager equity: {e}")

        # Check stop-loss for current position
        if self.current_inventory != Decimal("0") and self.mid_price is not None:
            # Get position information
            position = None
            positions = self.cache.positions_open(self.instrument_id)
            if positions:
                position = positions[0]

            if position is not None:
                # Check if position has hit stop loss
                entry_price = position.avg_px_open
                position_side = 'LONG' if position.side.name == 'LONG' else 'SHORT'

                if self.risk_manager.check_position_stop_loss(entry_price, self.mid_price, position_side):
                    self._log.warning(f"Stop loss triggered for {position_side} position at {self.mid_price}")

                    # Close the position
                    self.close_position(position)

                    # Cancel all orders
                    self.cancel_all_orders()
