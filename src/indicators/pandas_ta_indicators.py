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

import numpy as np
import pandas as pd
from typing import Any, Callable, Dict, Optional, Union

from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import PriceType

# Try to import pandas_ta, or use a simple implementation if it fails
try:
    import pandas_ta as ta
except ImportError:
    # Simple implementation of RSI and moving averages
    class SimpleTa:
        @staticmethod
        def rsi(series, length=14):
            # Calculate price changes
            delta = series.diff()

            # Separate gains and losses
            gains = delta.copy()
            losses = delta.copy()
            gains[gains < 0] = 0
            losses[losses > 0] = 0
            losses = -losses

            # Calculate average gains and losses
            avg_gain = gains.rolling(window=length).mean()
            avg_loss = losses.rolling(window=length).mean()

            # Calculate RS and RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi

        @staticmethod
        def sma(series, length=10):
            return series.rolling(window=length).mean()

        @staticmethod
        def ema(series, length=10):
            return series.ewm(span=length, adjust=False).mean()

        @staticmethod
        def wma(series, length=10):
            # Simple weighted moving average
            weights = np.arange(1, length + 1)
            return series.rolling(window=length).apply(lambda x: np.sum(weights * x) / weights.sum(), raw=True)

    ta = SimpleTa()


class PandasTaIndicator(Indicator):
    """
    Generic indicator implementation using pandas-ta.

    This class allows using any indicator from the pandas-ta library with Nautilus Trader.

    Parameters
    ----------
    bar_type : BarType
        The bar type for the indicator.
    indicator_name : str
        The name of the indicator function to use (e.g., 'rsi', 'sma').
    params : Dict[str, Any]
        Parameters to pass to the indicator function.
    price_type : PriceType
        The price type for the indicator.
    output_index : int
        The index of the output to use if the indicator returns multiple values.
    """

    def __init__(
        self,
        bar_type: BarType,
        indicator_name: str,
        params: Dict[str, Any] = None,
        price_type: PriceType = PriceType.LAST,
        output_index: int = 0,
    ):
        super().__init__([])  # Pass an empty list as params

        self.bar_type = bar_type
        self.indicator_name = indicator_name
        self.indicator_params = params or {}
        self.price_type = price_type
        self.output_index = output_index

        # Get the period parameter if it exists
        self.period = self.indicator_params.get("length", 14)

        # Initialize arrays
        self.prices = np.array([])
        self.indicator_values = np.array([])

    def handle_bar(self, bar: Bar) -> None:
        """
        Update the indicator with the given bar.

        Parameters
        ----------
        bar : Bar
            The update bar.
        """
        # Extract price from bar based on price_type
        if self.price_type == PriceType.LAST:
            price = bar.close.as_double()
        elif self.price_type == PriceType.BID:
            price = bar.bid_close.as_double()
        elif self.price_type == PriceType.ASK:
            price = bar.ask_close.as_double()
        elif self.price_type == PriceType.MID:
            price = (bar.bid_close.as_double() + bar.ask_close.as_double()) / 2.0
        else:
            price = bar.close.as_double()  # Default to close

        # Append price to array
        self.prices = np.append(self.prices, price)

        # Calculate indicator if we have enough data
        if len(self.prices) >= self.period:
            # Convert to pandas Series for pandas-ta
            price_series = pd.Series(self.prices)

            # Calculate indicator based on name
            if self.indicator_name == 'rsi':
                result = self._calculate_rsi(price_series)
            elif self.indicator_name == 'sma':
                result = self._calculate_sma(price_series)
            elif self.indicator_name == 'ema':
                result = self._calculate_ema(price_series)
            elif self.indicator_name == 'wma':
                result = self._calculate_wma(price_series)
            else:
                # Default to SMA if indicator not recognized
                result = self._calculate_sma(price_series)

            # Add the result to our values
            self.indicator_values = np.append(self.indicator_values, result)

        # Keep only the needed prices
        if len(self.prices) > self.period * 2:  # Keep twice the period for safety
            self.prices = self.prices[-(self.period * 2):]

        # Keep only the needed indicator values
        if len(self.indicator_values) > self.period:
            self.indicator_values = self.indicator_values[-self.period:]

    def _calculate_rsi(self, price_series: pd.Series) -> float:
        """
        Calculate RSI using pandas.

        Parameters
        ----------
        price_series : pd.Series
            The price series.

        Returns
        -------
        float
            The RSI value.
        """
        length = self.indicator_params.get("length", 14)

        # Calculate price changes
        delta = price_series.diff()

        # Separate gains and losses
        gains = delta.copy()
        losses = delta.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = -losses

        # Calculate average gains and losses
        avg_gain = gains.rolling(window=length).mean()
        avg_loss = losses.rolling(window=length).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1]

    def _calculate_sma(self, price_series: pd.Series) -> float:
        """
        Calculate SMA using pandas.

        Parameters
        ----------
        price_series : pd.Series
            The price series.

        Returns
        -------
        float
            The SMA value.
        """
        length = self.indicator_params.get("length", 14)
        return price_series.rolling(window=length).mean().iloc[-1]

    def _calculate_ema(self, price_series: pd.Series) -> float:
        """
        Calculate EMA using pandas.

        Parameters
        ----------
        price_series : pd.Series
            The price series.

        Returns
        -------
        float
            The EMA value.
        """
        length = self.indicator_params.get("length", 14)
        return price_series.ewm(span=length, adjust=False).mean().iloc[-1]

    def _calculate_wma(self, price_series: pd.Series) -> float:
        """
        Calculate WMA using pandas.

        Parameters
        ----------
        price_series : pd.Series
            The price series.

        Returns
        -------
        float
            The WMA value.
        """
        length = self.indicator_params.get("length", 14)
        weights = np.arange(1, length + 1)
        return price_series.rolling(window=length).apply(
            lambda x: np.sum(weights * x) / weights.sum(), raw=True
        ).iloc[-1]

    @property
    def value(self) -> Optional[float]:
        """
        Return the current indicator value.

        Returns
        -------
        Optional[float]
            The current value.
        """
        if len(self.indicator_values) == 0:
            return None
        return self.indicator_values[-1]

    @property
    def has_inputs(self) -> bool:
        """
        Return whether the indicator has inputs.

        Returns
        -------
        bool
            True if the indicator has inputs, else False.
        """
        return len(self.prices) >= self.period

    def reset(self) -> None:
        """
        Reset the indicator.
        """
        self.prices = np.array([])
        self.indicator_values = np.array([])


# No convenience classes - use the base PandasTaIndicator directly
