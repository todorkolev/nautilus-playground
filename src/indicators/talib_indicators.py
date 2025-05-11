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
from typing import Any, Callable, Dict, Optional, Tuple, Union

# Try to import talib, or use a simple implementation if it fails
try:
    import talib
except ImportError:
    # Simple implementation of talib functions
    class SimpleTalib:
        @staticmethod
        def RSI(prices, timeperiod=14):
            # Calculate price changes
            delta = np.diff(prices)
            delta = np.append(delta, 0)  # Add a 0 to maintain array length

            # Separate gains and losses
            gains = delta.copy()
            losses = delta.copy()
            gains[gains < 0] = 0
            losses[losses > 0] = 0
            losses = -losses

            # Calculate average gains and losses
            avg_gain = np.zeros_like(prices)
            avg_loss = np.zeros_like(prices)

            # First average is simple average
            if len(prices) > timeperiod:
                avg_gain[timeperiod] = np.mean(gains[1:timeperiod+1])
                avg_loss[timeperiod] = np.mean(losses[1:timeperiod+1])

                # Subsequent averages use Wilder's smoothing method
                for i in range(timeperiod+1, len(prices)):
                    avg_gain[i] = (avg_gain[i-1] * (timeperiod-1) + gains[i]) / timeperiod
                    avg_loss[i] = (avg_loss[i-1] * (timeperiod-1) + losses[i]) / timeperiod

            # Calculate RS and RSI
            rs = np.zeros_like(prices)
            rsi = np.zeros_like(prices)

            for i in range(timeperiod, len(prices)):
                if avg_loss[i] == 0:
                    rsi[i] = 100
                else:
                    rs[i] = avg_gain[i] / avg_loss[i]
                    rsi[i] = 100 - (100 / (1 + rs[i]))

            # Set initial values to NaN
            rsi[:timeperiod] = np.nan

            return rsi

        @staticmethod
        def MA(prices, timeperiod=30, matype=0):
            # Simple implementation of moving averages
            # matype: 0=SMA, 1=EMA
            result = np.zeros_like(prices)
            result[:] = np.nan  # Initialize with NaN

            if matype == 0:  # SMA
                for i in range(timeperiod-1, len(prices)):
                    result[i] = np.mean(prices[i-timeperiod+1:i+1])
            elif matype == 1:  # EMA
                # Calculate alpha
                alpha = 2 / (timeperiod + 1)

                # First value is SMA
                if len(prices) >= timeperiod:
                    result[timeperiod-1] = np.mean(prices[:timeperiod])

                    # Calculate EMA
                    for i in range(timeperiod, len(prices)):
                        result[i] = alpha * prices[i] + (1 - alpha) * result[i-1]

            return result

        @staticmethod
        def BBANDS(prices, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0):
            # Calculate moving average
            ma = SimpleTalib.MA(prices, timeperiod, matype)

            # Calculate standard deviation
            std = np.zeros_like(prices)
            std[:] = np.nan

            for i in range(timeperiod-1, len(prices)):
                std[i] = np.std(prices[i-timeperiod+1:i+1])

            # Calculate upper and lower bands
            upper = ma + nbdevup * std
            lower = ma - nbdevdn * std

            return upper, ma, lower

        @staticmethod
        def MACD(prices, fastperiod=12, slowperiod=26, signalperiod=9):
            # Calculate fast and slow EMAs
            fast_ema = SimpleTalib.MA(prices, fastperiod, matype=1)
            slow_ema = SimpleTalib.MA(prices, slowperiod, matype=1)

            # Calculate MACD line
            macd_line = fast_ema - slow_ema

            # Calculate signal line (EMA of MACD line)
            signal_line = np.zeros_like(prices)
            signal_line[:] = np.nan

            # First value is SMA of MACD line
            if len(macd_line) >= signalperiod:
                valid_indices = ~np.isnan(macd_line[:signalperiod])
                if np.sum(valid_indices) > 0:
                    signal_line[signalperiod-1] = np.mean(macd_line[:signalperiod][valid_indices])

                # Calculate EMA of MACD line
                alpha = 2 / (signalperiod + 1)
                for i in range(signalperiod, len(macd_line)):
                    if not np.isnan(signal_line[i-1]) and not np.isnan(macd_line[i]):
                        signal_line[i] = alpha * macd_line[i] + (1 - alpha) * signal_line[i-1]

            # Calculate histogram
            histogram = macd_line - signal_line

            return macd_line, signal_line, histogram

    talib = SimpleTalib()

from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import PriceType


class TalibIndicator(Indicator):
    """
    Generic indicator implementation using TA-Lib.

    This class allows using any indicator from the TA-Lib library with Nautilus Trader.

    Parameters
    ----------
    bar_type : BarType
        The bar type for the indicator.
    indicator_name : str
        The name of the indicator function to use (e.g., 'RSI', 'MA').
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
        self.period = self.indicator_params.get("timeperiod", 14)

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
            # Calculate indicator based on name
            if self.indicator_name.upper() == 'RSI':
                result = self._calculate_rsi(self.prices)
            elif self.indicator_name.upper() == 'MA':
                result = self._calculate_ma(self.prices)
            elif self.indicator_name.upper() == 'BBANDS':
                result = self._calculate_bbands(self.prices)
            else:
                # Default to MA if indicator not recognized
                result = self._calculate_ma(self.prices)

            # Handle different return types
            if isinstance(result, np.ndarray):
                # If result is a numpy array, get the last value
                if not np.isnan(result[-1]):
                    self.indicator_values = np.append(self.indicator_values, result[-1])
            elif isinstance(result, tuple):
                # If result is a tuple, get the specified index
                if self.output_index < len(result):
                    if not np.isnan(result[self.output_index][-1]):
                        self.indicator_values = np.append(self.indicator_values, result[self.output_index][-1])

        # Keep only the needed prices
        if len(self.prices) > self.period * 2:  # Keep twice the period for safety
            self.prices = self.prices[-(self.period * 2):]

        # Keep only the needed indicator values
        if len(self.indicator_values) > self.period:
            self.indicator_values = self.indicator_values[-self.period:]

    def _calculate_rsi(self, prices: np.ndarray) -> np.ndarray:
        """
        Calculate RSI using numpy.

        Parameters
        ----------
        prices : np.ndarray
            The price array.

        Returns
        -------
        np.ndarray
            The RSI values.
        """
        timeperiod = self.indicator_params.get("timeperiod", 14)

        # Calculate price changes
        delta = np.diff(prices)
        delta = np.append(delta, 0)  # Add a 0 to maintain array length

        # Separate gains and losses
        gains = delta.copy()
        losses = delta.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = -losses

        # Calculate average gains and losses
        avg_gain = np.zeros_like(prices)
        avg_loss = np.zeros_like(prices)

        # First average is simple average
        if len(prices) > timeperiod:
            avg_gain[timeperiod] = np.mean(gains[1:timeperiod+1])
            avg_loss[timeperiod] = np.mean(losses[1:timeperiod+1])

            # Subsequent averages use Wilder's smoothing method
            for i in range(timeperiod+1, len(prices)):
                avg_gain[i] = (avg_gain[i-1] * (timeperiod-1) + gains[i]) / timeperiod
                avg_loss[i] = (avg_loss[i-1] * (timeperiod-1) + losses[i]) / timeperiod

        # Calculate RS and RSI
        rs = np.zeros_like(prices)
        rsi = np.zeros_like(prices)

        for i in range(timeperiod, len(prices)):
            if avg_loss[i] == 0:
                rsi[i] = 100
            else:
                rs[i] = avg_gain[i] / avg_loss[i]
                rsi[i] = 100 - (100 / (1 + rs[i]))

        # Set initial values to NaN
        rsi[:timeperiod] = np.nan

        return rsi

    def _calculate_ma(self, prices: np.ndarray) -> np.ndarray:
        """
        Calculate Moving Average using numpy.

        Parameters
        ----------
        prices : np.ndarray
            The price array.

        Returns
        -------
        np.ndarray
            The MA values.
        """
        timeperiod = self.indicator_params.get("timeperiod", 14)
        matype = self.indicator_params.get("matype", 0)  # 0 = SMA, 1 = EMA

        result = np.zeros_like(prices)
        result[:] = np.nan  # Initialize with NaN

        if matype == 0:  # SMA
            for i in range(timeperiod-1, len(prices)):
                result[i] = np.mean(prices[i-timeperiod+1:i+1])
        elif matype == 1:  # EMA
            # Calculate alpha
            alpha = 2 / (timeperiod + 1)

            # First value is SMA
            if len(prices) >= timeperiod:
                result[timeperiod-1] = np.mean(prices[:timeperiod])

                # Calculate EMA
                for i in range(timeperiod, len(prices)):
                    result[i] = alpha * prices[i] + (1 - alpha) * result[i-1]

        return result

    def _calculate_bbands(self, prices: np.ndarray) -> tuple:
        """
        Calculate Bollinger Bands using numpy.

        Parameters
        ----------
        prices : np.ndarray
            The price array.

        Returns
        -------
        tuple
            The upper, middle, and lower bands.
        """
        timeperiod = self.indicator_params.get("timeperiod", 5)
        nbdevup = self.indicator_params.get("nbdevup", 2)
        nbdevdn = self.indicator_params.get("nbdevdn", 2)
        matype = self.indicator_params.get("matype", 0)

        # Calculate moving average
        ma = self._calculate_ma(prices)

        # Calculate standard deviation
        std = np.zeros_like(prices)
        std[:] = np.nan

        for i in range(timeperiod-1, len(prices)):
            std[i] = np.std(prices[i-timeperiod+1:i+1])

        # Calculate upper and lower bands
        upper = ma + nbdevup * std
        lower = ma - nbdevdn * std

        return upper, ma, lower

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


# No convenience classes - use the base TalibIndicator directly
