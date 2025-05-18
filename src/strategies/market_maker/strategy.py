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

    # Core trading parameters
    trade_size: Decimal = Decimal("0.01")
    max_inventory: Decimal = Decimal("0.05")

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
        self.trade_size = config.trade_size
        self.max_inventory = config.max_inventory

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

        # ADX for trend strength
        self.adx = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="adx",
            params={"length": self.adx_period},
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
            output_index=1,  # Middle band (mean)
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
                self._log.warning(f"Instrument {self.instrument_id} not found in cache")
                from nautilus_trader.test_kit.providers import TestInstrumentProvider
                self.instrument = TestInstrumentProvider.btcusdt_binance()
                self._log.info(f"Created dummy instrument {self.instrument_id} for backtesting")

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

                    # Negative autocorrelation suggests mean reversion
                    is_mean_reverting = (autocorr < float(self._autocorr_threshold) and
                                        adx_value < self.adx_threshold)

                    # Detect trend direction for trend skew
                    self.skip_buy_side = False
                    self.skip_sell_side = False

                    if self.enable_trend_skew and adx_value >= self.trend_strength_threshold:
                        # Get +DI and -DI values for trend direction
                        plus_di = None
                        minus_di = None

                        # Try to get +DI and -DI from indicator outputs
                        try:
                            # Assuming the ADX indicator outputs include +DI and -DI
                            # This may need adjustment based on the actual implementation
                            adx_outputs = self.adx.outputs
                            if isinstance(adx_outputs, dict) and 'plus_di' in adx_outputs and 'minus_di' in adx_outputs:
                                plus_di = adx_outputs['plus_di']
                                minus_di = adx_outputs['minus_di']

                            # If we couldn't get +DI and -DI from outputs, use price action
                            if plus_di is None or minus_di is None:
                                # Simple trend detection based on recent price action
                                short_ma = np.mean(prices[-5:])
                                long_ma = np.mean(prices[-20:])

                                if short_ma > long_ma:
                                    plus_di = 25
                                    minus_di = 15
                                else:
                                    plus_di = 15
                                    minus_di = 25

                            # Determine trend direction
                            if plus_di > minus_di:
                                self.current_trend = 'UP'
                                self.skip_sell_side = True  # Skip sell orders in uptrend
                                self._log.info(f"Detected uptrend: ADX={adx_value:.2f}, +DI={plus_di:.2f}, -DI={minus_di:.2f}")
                            else:
                                self.current_trend = 'DOWN'
                                self.skip_buy_side = True  # Skip buy orders in downtrend
                                self._log.info(f"Detected downtrend: ADX={adx_value:.2f}, +DI={plus_di:.2f}, -DI={minus_di:.2f}")
                        except Exception as e:
                            self._log.warning(f"Error detecting trend direction: {e}")
                            self.current_trend = None
                    else:
                        self.current_trend = None

                    if is_mean_reverting:
                        self._log.info(f"Detected mean-reverting market: ADX={adx_value:.2f}, Autocorr={autocorr:.4f}")

                        # Set grid parameters for mean reversion trading
                        self.grid_mean = Decimal(str(np.mean(prices[-self.bbands_length:])))
                        self.grid_std_dev = Decimal(str(np.std(prices[-self.bbands_length:])))

                        # In mean-reverting markets, don't skip either side
                        self.skip_buy_side = False
                        self.skip_sell_side = False
                    else:
                        self._log.debug(f"Detected trending market: ADX={adx_value:.2f}, Autocorr={autocorr:.4f}")

                    # Update state
                    self.is_mean_reverting = is_mean_reverting

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

    def _compute_order_params(self, level: int) -> Optional[Dict]:
        """
        Compute order parameters for a specific level.

        Parameters
        ----------
        level : int
            The level index (0 for closest to mid price, increasing for further levels)

        Returns
        -------
        dict or None
            Dictionary containing order parameters or None if calculation failed
        """
        if self.mid_price is None or self.spread is None or self.instrument is None:
            return None

        reference_price = self._compute_reference_price()
        if reference_price is None:
            return None

        # Calculate inventory skew factor
        inventory_skew_factor = Decimal("1.0")
        if self.inventory_skew_enabled:
            # Calculate current inventory as percentage of max inventory
            current_inventory_pct = self.current_inventory / self.max_inventory if self.max_inventory != 0 else Decimal("0")

            # Calculate skew based on difference from target
            inventory_skew = current_inventory_pct - self._target_inventory_pct

            # Apply skew factor (reduce buy size when inventory > target, reduce sell size when inventory < target)
            inventory_skew_factor = Decimal("1.0") - (inventory_skew * Decimal("0.5"))
            inventory_skew_factor = max(min(inventory_skew_factor, Decimal("2.0")), Decimal("0.0"))

        # Calculate level offset
        level_offset_pct = self._level_spacing_pct * Decimal(str(level))

        # Calculate relative spread as percentage of price
        relative_spread_pct = self.spread / self.mid_price if self.mid_price != 0 else Decimal("0.001")

        # Calculate base spread percentage with bounds
        base_spread_pct = max(min(self._spread_multiplier * relative_spread_pct,
                                self._max_spread_pct),
                            self._min_spread_pct)

        # Apply ATR adjustment if available
        if self.atr.initialized and self.atr.value is not None:
            try:
                atr_value = Decimal(str(self.atr.value))
                atr_factor = atr_value / (self.mid_price * Decimal("0.01")) if self.mid_price != 0 else Decimal("1.0")

                # Adjust spread based on market regime
                if self.is_mean_reverting:
                    # Tighter spreads in mean-reverting markets
                    base_spread_pct = base_spread_pct * (Decimal("1.0") + atr_factor * Decimal("0.3"))
                else:
                    # Wider spreads in trending markets
                    base_spread_pct = base_spread_pct * (Decimal("1.0") + atr_factor * Decimal("0.7"))
            except (ValueError, TypeError):
                # Handle case where ATR value is NaN or invalid
                self._log.warning(f"Invalid ATR value: {self.atr.value}, using base spread")

        # Calculate bid and ask prices
        bid_spread = base_spread_pct / Decimal("2.0") + level_offset_pct
        ask_spread = base_spread_pct / Decimal("2.0") + level_offset_pct

        # Ensure prices are valid
        try:
            # Use reference price for price calculation
            bid_price = reference_price * (Decimal("1.0") - bid_spread)
            ask_price = reference_price * (Decimal("1.0") + ask_spread)

            # Check for NaN or invalid values
            if bid_price.is_nan() or ask_price.is_nan():
                self._log.warning(f"Generated NaN price values, skipping order placement")
                return None
        except Exception as e:
            self._log.error(f"Error calculating prices: {e}")
            return None

        # Adjust for inventory skew
        buy_size = self.trade_size * inventory_skew_factor
        sell_size = self.trade_size * (Decimal("2.0") - inventory_skew_factor)

        # Apply dynamic sizing based on volatility if enabled
        if self.dynamic_sizing and self.atr.initialized and self.atr.value is not None:
            try:
                atr_value = Decimal(str(self.atr.value))
                volatility_ratio = atr_value / (self.mid_price * Decimal("0.01"))

                # Scale size based on volatility
                volatility_adjustment = self._volatility_factor * volatility_ratio

                # Limit the adjustment to reasonable bounds
                volatility_adjustment = max(min(volatility_adjustment, Decimal("2.0")), Decimal("0.5"))

                buy_size = buy_size * volatility_adjustment
                sell_size = sell_size * volatility_adjustment

                self._log.debug(f"Dynamic sizing: volatility_ratio={volatility_ratio:.4f}, adjustment={volatility_adjustment:.4f}")
            except (ValueError, TypeError):
                self._log.warning(f"Invalid ATR value for dynamic sizing: {self.atr.value}")

        # Ensure minimum size
        min_size = self.instrument.min_quantity
        buy_size = max(buy_size, min_size)
        sell_size = max(sell_size, min_size)

        return {
            "bid_price": bid_price,
            "ask_price": ask_price,
            "buy_size": buy_size,
            "sell_size": sell_size,
            "level": level,
        }

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

            # Place orders
            self._place_limit_order(OrderSide.BUY, params["bid_price"], params["buy_size"])
            self._place_limit_order(OrderSide.SELL, params["ask_price"], params["sell_size"])

    def refresh_orders(self) -> None:
        """
        Refresh all orders based on current market conditions and market regime.
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

        # Cancel existing orders
        self.cancel_all_orders()

        # Check for momentum overlay signals
        if self.enable_momentum_overlay and not self.momentum_overlay.active_momentum_trade:
            # Get indicator values for momentum detection
            rsi_value = self.rsi.value if self.rsi.initialized and self.rsi.value is not None else 50.0
            bbands_upper = None
            bbands_lower = None
            bbands_middle = None

            # Try to get Bollinger Bands values
            try:
                if self.bbands.initialized and hasattr(self.bbands, 'outputs'):
                    bbands_outputs = self.bbands.outputs
                    if isinstance(bbands_outputs, dict):
                        if 'upper' in bbands_outputs and 'lower' in bbands_outputs and 'middle' in bbands_outputs:
                            bbands_upper = Decimal(str(bbands_outputs['upper']))
                            bbands_lower = Decimal(str(bbands_outputs['lower']))
                            bbands_middle = Decimal(str(bbands_outputs['middle']))
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

                # Calculate momentum trade size
                momentum_size = self.momentum_overlay.calculate_momentum_trade_size(self.trade_size)

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

                    # Update momentum overlay state
                    self.momentum_overlay.start_momentum_trade(direction, self.mid_price)

                elif direction == 'SHORT':
                    self._log.info(f"Executing momentum SHORT trade with size {momentum_size}")
                    # Create and submit market order
                    order = self.order_factory.market(
                        instrument_id=self.instrument_id,
                        order_side=OrderSide.SELL,
                        quantity=self.instrument.make_qty(momentum_size),
                    )
                    self.submit_order(order)

                    # Update momentum overlay state
                    self.momentum_overlay.start_momentum_trade(direction, self.mid_price)

                # Skip regular order placement when executing momentum trade
                return

        # Check if we have an active momentum trade
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

                # Skip regular order placement when exiting momentum trade
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

        # Compute parameters for each level
        params_list = []
        for level in range(self.order_levels):
            # Use SpreadCapture module
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
            )

            if params is not None:
                params_list.append(params)

        # Submit orders
        self._submit_orders(params_list)

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

        # Adjust price to ensure it's not a taker order if post_only is True
        if self.post_only and self.last_quote is not None:
            if side == OrderSide.BUY:
                # If the buy price is higher than or equal to the ask price, it would be a taker order
                if price >= self.last_quote.ask_price:
                    # Adjust price to be slightly below the ask price
                    price = self.last_quote.ask_price * Decimal("0.9995")
                    self._log.debug(f"Adjusted BUY price to {price} to avoid taker order")
            else:  # SELL
                # If the sell price is lower than or equal to the bid price, it would be a taker order
                if price <= self.last_quote.bid_price:
                    # Adjust price to be slightly above the bid price
                    price = self.last_quote.bid_price * Decimal("1.0005")
                    self._log.debug(f"Adjusted SELL price to {price} to avoid taker order")

        # Create the order
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
