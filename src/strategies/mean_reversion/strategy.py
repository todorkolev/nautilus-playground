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
Implementation of a Mean Reversion Strategy.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import field
from pathlib import Path

import numpy as np
import yaml
from scipy.optimize import minimize
from statsmodels.tsa.stattools import adfuller

from nautilus_trader.backtest.node import BacktestDataConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import BarAggregation, PriceType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price
from nautilus_trader.trading.strategy import Strategy

from src.indicators.pandas_ta_indicator import PandasTaIndicator
from src.strategies.position_management import Position, Side, ShrinkingRangePosition, TrailingStopPosition
from src.strategies.mean_reversion.ml_model import LogisticRegressionModel, DecisionTreeModel, XGBoostModel


class MeanReversionStrategyConfig(StrategyConfig):
    """
    Configuration for the Mean Reversion Strategy.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID for the strategy.
    bar_type : BarType
        The bar type for the strategy.
    trade_size : Decimal
        The trade size for the strategy.
    lookback : int
        The lookback period for the strategy.
    std_dev_threshold : float
        The standard deviation threshold for the strategy.
    positions_per_side : int
        The maximum number of positions per side.
    take_profit_std_dev_multiplier : float
        The take profit standard deviation multiplier.
    stop_loss_std_dev_multiplier : float
        The stop loss standard deviation multiplier.
    take_profit_hold : float
        The time to hold the take profit price (in minutes).
    take_profit_decay : float
        The time to decay the take profit price (in minutes).
    stop_loss_hold : float
        The time to hold the stop loss price (in minutes).
    stop_loss_decay : float
        The time to decay the stop loss price (in minutes).
    trailing_stop_pct : float
        The trailing stop percentage.
    ml_model_type : str
        The type of ML model to use.
    ml_confidence_threshold : float
        The confidence threshold for ML predictions.
    ml_features : List[str]
        The features to use for ML predictions.
    trend_adx_threshold : float
        The ADX threshold for trend following.
    extreme_deviation_multiplier : float
        The multiplier for extreme deviations.
    adx_daily_threshold : float
        The ADX daily threshold for mean reversion.
    adx_hourly_threshold : float
        The ADX hourly threshold for mean reversion.
    adf_pvalue_threshold : float
        The p-value threshold for stationarity test.
    grid_level_threshold : float
        The threshold for creating a new grid level.
    min_training_samples : int
        The minimum number of samples required for ML training.
    adx_length : int
        The length parameter for ADX indicator.
    rsi_length : int
        The length parameter for RSI indicator.
    macd_fast : int
        The fast period for MACD indicator.
    macd_slow : int
        The slow period for MACD indicator.
    macd_signal : int
        The signal period for MACD indicator.
    bbands_length : int
        The length parameter for Bollinger Bands indicator.
    bbands_std : int
        The standard deviation parameter for Bollinger Bands indicator.
    atr_length : int
        The length parameter for ATR indicator.
    ml_training_lookback : int
        The number of bars to look ahead for ML training labels.
    """

    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("0.1")
    lookback: int = 168  # 7 days of hourly data
    std_dev_threshold: float = 2.0
    positions_per_side: int = 3
    take_profit_std_dev_multiplier: float = 1.5
    stop_loss_std_dev_multiplier: float = 2.0
    take_profit_hold: float = 8 * 60  # 8 hours in minutes
    take_profit_decay: float = 48 * 60  # 48 hours in minutes
    stop_loss_hold: float = 8 * 60  # 8 hours in minutes
    stop_loss_decay: float = 48 * 60  # 48 hours in minutes
    trailing_stop_pct: float = 0.005  # 0.5%
    ml_model_type: str = "xgboost"
    ml_confidence_threshold: float = 0.6
    ml_features: List[str] = field(default_factory=lambda: ["adx", "rsi", "macd", "bbands", "atr", "ou_theta", "ou_mu", "ou_sigma", "adf_pvalue", "distance", "returns"])
    trend_adx_threshold: float = 50.0
    extreme_deviation_multiplier: float = 2.0
    # New parameters to replace magic numbers
    adx_daily_threshold: float = 70.0
    adx_hourly_threshold: float = 80.0
    adf_pvalue_threshold: float = 0.05
    grid_level_threshold: float = 0.5
    min_training_samples: int = 30
    # Indicator parameters
    adx_length: int = 14
    rsi_length: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bbands_length: int = 20
    bbands_std: int = 2
    atr_length: int = 14

    # ML training parameters
    ml_training_lookback: int = 24
    recent_returns_lookback: int = 5
    # Logging parameters
    log_interval: int = 10

    # OU process parameters
    initial_theta: float = 0.5

    @classmethod
    def from_yaml(cls, path: str) -> "MeanReversionStrategyConfig":
        """
        Create a configuration from a YAML file.

        Parameters
        ----------
        path : str
            The path to the YAML file.

        Returns
        -------
        MeanReversionStrategyConfig
            The configuration.
        """
        with open(path, "r") as file:
            config_dict = yaml.safe_load(file)

        params = config_dict.get("parameters", {})

        # Parse instrument_id
        instrument_id_str = params.get("instrument_id")
        if instrument_id_str:
            instrument_id = InstrumentId.from_str(instrument_id_str)
        else:
            raise ValueError("instrument_id is required")

        # Parse bar_type
        bar_type_str = params.get("bar_type")
        if bar_type_str:
            bar_type = BarType.from_str(bar_type_str)
        else:
            raise ValueError("bar_type is required")

        # Create the configuration
        return cls(
            instrument_id=instrument_id,
            bar_type=bar_type,
            trade_size=Decimal(str(params.get("trade_size", 0.1))),
            lookback=params.get("lookback", 168),
            std_dev_threshold=params.get("std_dev_threshold", 2.0),
            positions_per_side=params.get("positions_per_side", 3),
            take_profit_std_dev_multiplier=params.get("take_profit_std_dev_multiplier", 1.5),
            stop_loss_std_dev_multiplier=params.get("stop_loss_std_dev_multiplier", 2.0),
            take_profit_hold=params.get("take_profit_hold", 8 * 60),
            take_profit_decay=params.get("take_profit_decay", 48 * 60),
            stop_loss_hold=params.get("stop_loss_hold", 8 * 60),
            stop_loss_decay=params.get("stop_loss_decay", 48 * 60),
            trailing_stop_pct=params.get("trailing_stop_pct", 0.005),
            ml_model_type=params.get("ml_model_type", "xgboost"),
            ml_confidence_threshold=params.get("ml_confidence_threshold", 0.6),
            ml_features=params.get("ml_features", ["adx", "rsi", "macd", "bbands", "atr", "ou_theta", "ou_mu", "ou_sigma", "adf_pvalue", "distance", "returns"]),
            trend_adx_threshold=params.get("trend_adx_threshold", 50.0),
            extreme_deviation_multiplier=params.get("extreme_deviation_multiplier", 2.0),
            # New parameters
            adx_daily_threshold=params.get("adx_daily_threshold", 70.0),
            adx_hourly_threshold=params.get("adx_hourly_threshold", 80.0),
            adf_pvalue_threshold=params.get("adf_pvalue_threshold", 0.05),
            grid_level_threshold=params.get("grid_level_threshold", 0.5),
            min_training_samples=params.get("min_training_samples", 30),
            # Indicator parameters
            adx_length=params.get("adx_length", 14),
            rsi_length=params.get("rsi_length", 14),
            macd_fast=params.get("macd_fast", 12),
            macd_slow=params.get("macd_slow", 26),
            macd_signal=params.get("macd_signal", 9),
            bbands_length=params.get("bbands_length", 20),
            bbands_std=params.get("bbands_std", 2),
            atr_length=params.get("atr_length", 14),

            # ML training parameters
            ml_training_lookback=params.get("ml_training_lookback", 24),
            recent_returns_lookback=params.get("recent_returns_lookback", 5),
            # Logging parameters
            log_interval=params.get("log_interval", 10),

            # OU process parameters
            initial_theta=params.get("initial_theta", 0.5),
        )


class MeanReversionStrategy(Strategy):
    """
    A Mean Reversion Strategy.

    This strategy identifies mean-reverting price action using statistical tests
    and trades accordingly. It uses ADX to determine trend strength and employs
    different position management techniques based on market conditions.
    It also uses machine learning to predict trend continuation when prices
    deviate significantly from the mean.

    Parameters
    ----------
    config : MeanReversionStrategyConfig
        The configuration for the strategy.
    """

    def __init__(self, config: MeanReversionStrategyConfig) -> None:
        super().__init__(config)

        # Configuration
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type
        self.daily_bar_type = BarType.from_str(f"{self.instrument_id.value}-1-DAY-LAST-EXTERNAL")
        self.trade_size = config.trade_size
        self.lookback = config.lookback
        self.std_dev_threshold = config.std_dev_threshold
        self.positions_per_side = config.positions_per_side
        self.take_profit_std_dev_multiplier = config.take_profit_std_dev_multiplier
        self.stop_loss_std_dev_multiplier = config.stop_loss_std_dev_multiplier
        self.take_profit_hold = config.take_profit_hold
        self.take_profit_decay = config.take_profit_decay
        self.stop_loss_hold = config.stop_loss_hold
        self.stop_loss_decay = config.stop_loss_decay
        self.trailing_stop_pct = config.trailing_stop_pct
        self.ml_model_type = config.ml_model_type
        self.ml_confidence_threshold = config.ml_confidence_threshold
        self.ml_features = config.ml_features
        self.trend_adx_threshold = config.trend_adx_threshold
        self.extreme_deviation_multiplier = config.extreme_deviation_multiplier

        # New parameters
        self.adx_daily_threshold = config.adx_daily_threshold
        self.adx_hourly_threshold = config.adx_hourly_threshold
        self.adf_pvalue_threshold = config.adf_pvalue_threshold
        self.grid_level_threshold = config.grid_level_threshold
        self.min_training_samples = config.min_training_samples

        # Indicator parameters
        self.adx_length = config.adx_length
        self.rsi_length = config.rsi_length
        self.macd_fast = config.macd_fast
        self.macd_slow = config.macd_slow
        self.macd_signal = config.macd_signal
        self.bbands_length = config.bbands_length
        self.bbands_std = config.bbands_std
        self.atr_length = config.atr_length

        # ML training parameters
        self.ml_training_lookback = config.ml_training_lookback
        self.recent_returns_lookback = config.recent_returns_lookback

        # Logging parameters
        self.log_interval = config.log_interval

        # Get instrument (may be None during backtesting setup)
        self.instrument = None  # Will be set in on_start

        # Create indicators using PandasTaIndicator
        self.adx_hourly = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="adx",
            params={"length": self.adx_length},
        )

        self.adx_daily = PandasTaIndicator(
            bar_type=self.daily_bar_type,
            indicator_name="adx",
            params={"length": self.adx_length},
        )

        self.rsi = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="rsi",
            params={"length": self.rsi_length},
        )

        self.macd = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="macd",
            params={"fast": self.macd_fast, "slow": self.macd_slow, "signal": self.macd_signal},
        )

        self.bbands = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="bbands",
            params={"length": self.bbands_length, "std": self.bbands_std},
        )

        self.atr = PandasTaIndicator(
            bar_type=self.bar_type,
            indicator_name="atr",
            params={"length": self.atr_length},
        )

        # Initialize ML model
        if self.ml_model_type == "logistic_regression":
            self.ml_model = LogisticRegressionModel(confidence_threshold=self.ml_confidence_threshold)
        elif self.ml_model_type == "decision_tree":
            self.ml_model = DecisionTreeModel(confidence_threshold=self.ml_confidence_threshold)
        elif self.ml_model_type == "xgboost":
            self.ml_model = XGBoostModel(confidence_threshold=self.ml_confidence_threshold)
        else:
            raise ValueError(f"Unknown ML model type: {self.ml_model_type}")

        # Initialize state variables
        self.hour_bars: List[Bar] = []
        self.grid_mean: Optional[float] = None
        self.grid_std_dev: Optional[float] = None
        self.ou_theta: Optional[float] = None
        self.ou_mu: Optional[float] = None
        self.ou_sigma: Optional[float] = None
        self.positions: Dict[Side, List[Position]] = {Side.LONG: [], Side.SHORT: []}
        self.last_grid_prices: Dict[Side, Optional[float]] = {Side.LONG: None, Side.SHORT: None}
        self.ml_model_trained = False
        self.ml_training_data = {
            "features": [],
            "labels": [],
        }

        # Register indicators for bars
        self.register_indicator_for_bars(self.bar_type, self.adx_hourly)
        self.register_indicator_for_bars(self.daily_bar_type, self.adx_daily)
        self.register_indicator_for_bars(self.bar_type, self.rsi)
        self.register_indicator_for_bars(self.bar_type, self.macd)
        self.register_indicator_for_bars(self.bar_type, self.bbands)
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
                self._log.error(f"Instrument {self.instrument_id} not found in cache")
                # from nautilus_trader.test_kit.providers import TestInstrumentProvider
                # self.instrument = TestInstrumentProvider.btcusdt_binance()
                # # Ensure price precision matches the data
                # self.instrument._price_precision = 6
                # self._log.info(f"Created dummy instrument {self.instrument_id} for backtesting with price_precision={self.instrument._price_precision}")

        # Then subscribe to live data
        self._log.info("Subscribing to live bar data...")
        self.subscribe_bars(self.bar_type)
        self.subscribe_bars(self.daily_bar_type)

    def on_bar(self, bar: Bar) -> None:
        """
        Actions to be performed when a bar is received.

        Parameters
        ----------
        bar : Bar
            The bar received.
        """

        self._log.info(f"Handling bar: {bar.bar_type}, ts={bar.ts_init}")

        # Store the bar
        if bar.bar_type == self.bar_type:
            self.hour_bars.append(bar)

            # Keep only the last 'lookback' number of bars
            if len(self.hour_bars) > self.lookback:
                self.hour_bars = self.hour_bars[-self.lookback:]

            # Log indicator status periodically
            if len(self.hour_bars) % self.log_interval == 0:
                self._log.info(f"ADX Hourly initialized: {self.adx_hourly.initialized}, value: {self.adx_hourly.value}")
                self._log.info(f"ADX Hourly has_inputs: {self.adx_hourly.has_inputs}")
                self._log.info(f"RSI initialized: {self.rsi.initialized}, value: {self.rsi.value}")

        elif bar.bar_type == self.daily_bar_type:
            # Manually update the daily indicators
            self.adx_daily.handle_bar(bar)

            # Log indicator status
            self._log.info(f"ADX Daily initialized: {self.adx_daily.initialized}, value: {self.adx_daily.value}")
            self._log.info(f"ADX Daily has_inputs: {self.adx_daily.has_inputs}")

        # Update positions
        for side in Side:
            for position in self.positions[side]:
                position.update(bar)

        # Check if we have enough data
        if len(self.hour_bars) < self.lookback:
            return

        # Rebalance portfolio
        self.rebalance_portfolio()

    def rebalance_portfolio(self) -> None:
        """
        Rebalance the portfolio based on current market conditions.
        """
        # Extract prices from bars
        prices = np.array([bar.close.as_double() for bar in self.hour_bars])
        log_prices = np.log(prices)
        returns = np.diff(log_prices)

        # Check if indicators are initialized
        if not self.adx_hourly.initialized or not self.adx_daily.initialized:
            self._log.info(f"ADX indicators not yet initialized. Have {len(self.hour_bars)} bars.")
            return

        self._log.info(f"ADX Daily: {self.adx_daily.value}, ADX Hourly: {self.adx_hourly.value}")
        self._log.info(f"Number of hour bars: {len(self.hour_bars)}")

        # Get current price safely
        current_price = None
        if len(self.hour_bars) > 0:
            current_price = self.hour_bars[-1].close.as_double()
        self._log.info(f"Current price: {current_price}")

        # Check for mean reversion conditions
        if self.adx_daily.value < self.adx_daily_threshold and self.adx_hourly.value < self.adx_hourly_threshold:
            self._log.info(f"ADX PASS - Daily: {self.adx_daily.value:.2f}, Hourly: {self.adx_hourly.value:.2f}")

            # Check for stationarity
            is_stationary, adf_pvalue = self.is_stationary(log_prices)
            if is_stationary:
                self._log.info("Price series is stationary")

                # Estimate Ornstein-Uhlenbeck parameters
                self.estimate_ou_parameters(prices, returns)

                # Calculate distance from mean
                if current_price is None:
                    self._log.warning(f"No price available for {self.instrument_id}")
                    return

                distance = self.get_grid_distance(current_price)
                self._log.info(f"Distance from mean: {distance:.2f} std devs")

                # Check if price is within threshold for mean reversion
                if abs(distance) <= self.std_dev_threshold:
                    # Determine position side
                    side = Side.SHORT if distance > 0 else Side.LONG
                    self._log.info(f"Mean reversion signal: {side.value}")

                    # Manage grid position
                    self.manage_grid_position(side, current_price, is_stationary)

                # Check if price is far from mean (extreme deviation)
                elif abs(distance) > self.std_dev_threshold * self.extreme_deviation_multiplier:
                    self._log.info(f"Extreme deviation detected: {distance:.2f} std devs")

                    # Collect features for ML prediction
                    features = self.extract_ml_features(adf_pvalue, distance, returns)

                    # Train ML model if not trained
                    if not self.ml_model_trained and len(self.ml_training_data["features"]) > self.min_training_samples:
                        self.train_ml_model()

                    # If model is trained, make prediction
                    if self.ml_model_trained:
                        prediction, confidence = self.ml_model.predict(features)
                        self._log.info(f"ML prediction: {prediction}, confidence: {confidence:.2f}")

                        # If confidence is high enough, switch to trend following
                        if confidence >= self.ml_confidence_threshold:
                            # Determine trend direction
                            trend_side = Side.LONG if distance > 0 else Side.SHORT
                            self._log.info(f"Switching to trend following: {trend_side.value}")

                            # Close all grid positions
                            self.close_all_positions()

                            # Open trend position
                            self.manage_trend_position(trend_side, current_price)
                    else:
                        self._log.info("ML model not trained yet, collecting data")
                        # Collect training data
                        self.collect_ml_training_data(features, distance)
            else:
                self._log.info("Price series is not stationary")

        # Check for trend following conditions
        elif self.adx_hourly.value > self.trend_adx_threshold:
            self._log.info(f"Strong trend detected: ADX Hourly: {self.adx_hourly.value:.2f}")

            # Calculate distance from mean if OU parameters are available
            if self.grid_mean is not None and self.grid_std_dev is not None and current_price is not None:
                distance = self.get_grid_distance(current_price)
                self._log.info(f"Distance from mean: {distance:.2f} std devs")

                # Determine trend direction using +DI and -DI
                plus_di = self.adx_hourly.additional_values.get('DMP')
                minus_di = self.adx_hourly.additional_values.get('DMN')

                plus_di_str = f"{plus_di:.2f}" if plus_di is not None else "None"
                minus_di_str = f"{minus_di:.2f}" if minus_di is not None else "None"
                self._log.info(f"+DI: {plus_di_str}, -DI: {minus_di_str}")

                if plus_di is not None and minus_di is not None:
                    # Determine trend side
                    if plus_di > minus_di and distance > 0:
                        trend_side = Side.LONG
                        self._log.info(f"Trend following signal: {trend_side.value}")
                        self.manage_trend_position(trend_side, current_price)
                    elif plus_di < minus_di and distance < 0:
                        trend_side = Side.SHORT
                        self._log.info(f"Trend following signal: {trend_side.value}")
                        self.manage_trend_position(trend_side, current_price)

    def is_stationary(self, log_prices: np.ndarray) -> Tuple[bool, float]:
        """
        Check if the price series is stationary using the ADF test.

        Parameters
        ----------
        log_prices : np.ndarray
            The log price series.

        Returns
        -------
        Tuple[bool, float]
            Whether the series is stationary and the p-value.
        """
        # Run ADF test
        result = adfuller(log_prices)
        p_value = result[1]

        # Series is stationary if p-value < threshold
        is_stationary = p_value < self.adf_pvalue_threshold

        self._log.info(f"ADF test p-value: {p_value:.4f}, stationary: {is_stationary}")

        return is_stationary, p_value

    def estimate_ou_parameters(self, prices: np.ndarray, returns: np.ndarray) -> None:
        """
        Estimate the parameters of the Ornstein-Uhlenbeck process.

        Parameters
        ----------
        prices : np.ndarray
            The price series.
        returns : np.ndarray
            The returns series.
        """
        def ou_likelihood(params):
            theta, mu, _ = params  # Ignore sigma for now
            likelihood = sum((returns - theta * (mu - np.log(prices[:-1])))**2)
            return likelihood

        # Initial guess for optimization
        initial_theta = 0.5  # Initial guess for mean reversion speed
        initial_mu = np.mean(np.log(prices))  # Initial guess for mean
        initial_sigma = np.std(returns)  # Initial guess for volatility

        # Minimize the negative log-likelihood
        res = minimize(ou_likelihood, [initial_theta, initial_mu, initial_sigma])
        theta, mu, sigma = res.x

        # Store the parameters
        self.grid_mean = np.exp(mu)
        self.grid_std_dev = np.std(prices)
        self.ou_theta = theta
        self.ou_mu = mu
        self.ou_sigma = sigma

        self._log.info(f"OU parameters: mean={self.grid_mean:.2f}, std_dev={self.grid_std_dev:.2f}, "
                      f"theta={self.ou_theta:.4f}, mu={self.ou_mu:.4f}, sigma={self.ou_sigma:.4f}")

    def get_grid_distance(self, price: float) -> float:
        """
        Calculate the distance from the current price to the mean in standard deviations.

        Parameters
        ----------
        price : float
            The current price.

        Returns
        -------
        float
            The distance in standard deviations.
        """
        if self.grid_mean is None or self.grid_std_dev is None:
            return 0.0

        return (price - self.grid_mean) / self.grid_std_dev

    def manage_grid_position(self, side: Side, current_price: float, is_stationary: bool) -> None:
        """
        Manage grid positions for mean reversion.

        Parameters
        ----------
        side : Side
            The position side.
        current_price : float
            The current price.
        is_stationary : bool
            Whether the price series is stationary. Currently not used but kept for future enhancements.
        """
        # Note: is_stationary parameter is not currently used but kept for future enhancements
        # Check if we already have the maximum number of positions for this side
        if len(self.positions[side]) >= self.positions_per_side:
            self._log.info(f"Maximum number of {side.value} positions reached")
            return

        # Check if we need to create a new grid level
        last_price = self.last_grid_prices[side]
        if last_price is None or abs(current_price - last_price) / self.grid_std_dev > self.grid_level_threshold:
            self._log.info(f"Creating new grid level for {side.value} at {current_price:.2f}")

            # Calculate take profit and stop loss prices
            take_profit_price = None
            stop_loss_price = None

            if side == Side.LONG:
                take_profit_price = current_price + self.take_profit_std_dev_multiplier * self.grid_std_dev
                stop_loss_price = current_price - self.stop_loss_std_dev_multiplier * self.grid_std_dev
            else:  # Side.SHORT
                take_profit_price = current_price - self.take_profit_std_dev_multiplier * self.grid_std_dev
                stop_loss_price = current_price + self.stop_loss_std_dev_multiplier * self.grid_std_dev

            # Create a new position
            position = ShrinkingRangePosition(
                strategy=self,
                instrument_id=self.instrument_id,
                side=side,
                quantity=self.trade_size,
                entry_price=current_price,
                take_profit_price=take_profit_price,
                stop_loss_price=stop_loss_price,
                take_profit_hold=self.take_profit_hold,
                take_profit_decay=self.take_profit_decay,
                stop_loss_hold=self.stop_loss_hold,
                stop_loss_decay=self.stop_loss_decay,
            )

            # Open the position
            position.market_open()

            # Add to positions list
            self.positions[side].append(position)

            # Update last grid price
            self.last_grid_prices[side] = current_price

    def manage_trend_position(self, side: Side, current_price: float) -> None:
        """
        Manage trend positions for trend following.

        Parameters
        ----------
        side : Side
            The position side.
        current_price : float
            The current price.
        """
        # Close any existing positions on the opposite side
        opposite_side = Side.SHORT if side == Side.LONG else Side.LONG
        for position in self.positions[opposite_side]:
            position.market_close()
        self.positions[opposite_side] = []

        # Check if we already have a trend position for this side
        if any(position._position_type == "trend" for position in self.positions[side]):
            self._log.info(f"Trend position for {side.value} already exists")
            return

        # Create a new trend position
        position = TrailingStopPosition(
            strategy=self,
            instrument_id=self.instrument_id,
            side=side,
            quantity=self.trade_size,
            entry_price=current_price,
            stop_loss_percentage=self.trailing_stop_pct,
        )

        # Open the position
        position.market_open()

        # Add to positions list
        self.positions[side].append(position)

    def close_all_positions(self) -> None:
        """
        Close all open positions.
        """
        for side in Side:
            for position in self.positions[side]:
                position.market_close()
            self.positions[side] = []

    def extract_ml_features(self, adf_pvalue: float, distance: float, returns: np.ndarray) -> np.ndarray:
        """
        Extract features for ML prediction.

        Parameters
        ----------
        adf_pvalue : float
            The p-value from the ADF test.
        distance : float
            The distance from the mean in standard deviations.
        returns : np.ndarray
            The returns series.

        Returns
        -------
        np.ndarray
            The feature vector.
        """
        features = []

        # Add ADX values
        features.append(self.adx_hourly.value)

        # Add RSI
        if self.rsi.initialized:
            features.append(self.rsi.value)
        else:
            features.append(50)

        # Add MACD
        if self.macd.initialized:
            features.append(self.macd.value)
        else:
            features.append(0)

        # Add Bollinger Bands
        if self.bbands.initialized:
            features.append(self.bbands.value)
        else:
            features.append(0)

        # Add ATR
        if self.atr.initialized:
            features.append(self.atr.value)
        else:
            features.append(0)

        # Add OU parameters
        features.append(self.ou_theta if self.ou_theta is not None else 0)
        features.append(self.ou_mu if self.ou_mu is not None else 0)
        features.append(self.ou_sigma if self.ou_sigma is not None else 0)

        # Add ADF p-value
        features.append(adf_pvalue)

        # Add distance
        features.append(distance)

        # Add recent returns
        features.append(np.mean(returns[-self.recent_returns_lookback:]) if len(returns) >= self.recent_returns_lookback else 0)

        return np.array(features)

    def collect_ml_training_data(self, features: np.ndarray, distance: float) -> None:
        """
        Collect training data for the ML model.

        Parameters
        ----------
        features : np.ndarray
            The feature vector.
        distance : float
            The distance from the mean in standard deviations.
        """
        # Store features
        self.ml_training_data["features"].append(features)

        # Create label based on whether the price continues to move away from the mean
        # 1 = trend continuation, 0 = mean reversion
        # For simplicity, we'll use the sign of the distance to determine the direction
        # and check if the next bars continue in that direction
        if len(self.hour_bars) >= self.ml_training_lookback:
            current_price = self.hour_bars[-1].close.as_double()
            future_price = self.hour_bars[-self.ml_training_lookback].close.as_double()
            price_change = future_price - current_price

            # If distance is positive and price increases, or distance is negative and price decreases,
            # then the trend continues
            trend_continues = (distance > 0 and price_change > 0) or (distance < 0 and price_change < 0)

            self.ml_training_data["labels"].append(1 if trend_continues else 0)

    def train_ml_model(self) -> None:
        """
        Train the ML model with collected data.
        """
        if len(self.ml_training_data["features"]) < self.min_training_samples or len(self.ml_training_data["labels"]) < self.min_training_samples:
            self._log.info("Not enough training data yet")
            return

        features = np.array(self.ml_training_data["features"])
        labels = np.array(self.ml_training_data["labels"])

        self._log.info(f"Training ML model with {len(features)} samples")

        # Train the model
        metrics = self.ml_model.train(features, labels)

        self._log.info(f"ML model trained. Metrics: {metrics}")

        self.ml_model_trained = True

    def on_order_filled(self, event: OrderFilled) -> None:
        """
        Actions to be performed when an order is filled.

        Parameters
        ----------
        event : OrderFilled
            The order filled event.
        """
        self._log.info(f"Order filled: {event}")

        # Update positions
        for side in Side:
            for position in self.positions[side]:
                if position._initial_order_id == event.client_order_id:
                    position._entry_price = event.last_px.as_double()
                    position._entry_time = datetime.fromtimestamp(event.ts_event / 1_000_000_000)
                    position._filled_quantity = event.last_qty
                    position._opened = True

                    self._log.info(f"Position opened: {side.value} at {position._entry_price:.2f}")

                    # Update take profit and stop loss orders
                    position._update_take_profit(position._take_profit_price)
                    position._update_stop_loss(position._stop_loss_price)
