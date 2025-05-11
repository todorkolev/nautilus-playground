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
Implementation of an Average Directional Index (ADX) indicator.
"""

from typing import Optional

import numpy as np

from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import PriceType


class AverageDirectionalIndex(Indicator):
    """
    An Average Directional Index (ADX) indicator.

    The ADX measures the strength of a trend, regardless of its direction.
    It is calculated using the Directional Movement Index (DMI).

    Parameters
    ----------
    bar_type : BarType
        The bar type for the indicator.
    period : int
        The period for the indicator (number of bars).
    price_type : PriceType
        The price type for the indicator (default: PriceType.LAST).
    """

    def __init__(
        self,
        bar_type: BarType,
        period: int,
        price_type: PriceType = PriceType.LAST,
    ):
        super().__init__([bar_type])

        self.period = period
        self.price_type = price_type
        self._initialized = False

        # Initialize arrays
        self.high_prices = np.array([])
        self.low_prices = np.array([])
        self.close_prices = np.array([])

        self.tr_values = np.array([])
        self.plus_dm_values = np.array([])
        self.minus_dm_values = np.array([])

        self.atr_values = np.array([])
        self.plus_di_values = np.array([])
        self.minus_di_values = np.array([])
        self.dx_values = np.array([])
        self.adx_values = np.array([])

    def handle_bar(self, bar: Bar) -> None:
        """
        Update the indicator with the given bar.

        Parameters
        ----------
        bar : Bar
            The update bar.
        """
        # Extract prices from bar
        high = bar.high.as_double()
        low = bar.low.as_double()
        close = bar.close.as_double()

        # Log for debugging
        print(f"ADX received bar: {bar.bar_type}, high={high}, low={low}, close={close}")

        # Append prices to arrays
        self.high_prices = np.append(self.high_prices, high)
        self.low_prices = np.append(self.low_prices, low)
        self.close_prices = np.append(self.close_prices, close)

        # Keep only the needed prices
        if len(self.high_prices) > self.period + 1:
            self.high_prices = self.high_prices[-(self.period + 1):]
            self.low_prices = self.low_prices[-(self.period + 1):]
            self.close_prices = self.close_prices[-(self.period + 1):]

        # Calculate ADX if we have enough data
        if len(self.high_prices) > 1:
            self._calculate_adx()

        # Check if indicator is now initialized
        if len(self.adx_values) > 0 and not self._initialized:
            self._initialized = True
            print(f"ADX indicator initialized with period {self.period}, values: {self.adx_values}")

        # Log current state
        print(f"ADX state: initialized={self._initialized}, high_prices={len(self.high_prices)}, adx_values={len(self.adx_values)}")

    def handle_quote_tick(self, tick: QuoteTick) -> None:
        """
        Update the indicator with the given quote tick.

        This method is a placeholder to satisfy the Indicator interface.
        ADX requires OHLC data, so it's not updated with quote ticks.

        Parameters
        ----------
        tick : QuoteTick
            The update tick.
        """
        # ADX requires OHLC data, so we don't update with quote ticks
        pass

    def handle_trade_tick(self, tick: TradeTick) -> None:
        """
        Update the indicator with the given trade tick.

        This method is a placeholder to satisfy the Indicator interface.
        ADX requires OHLC data, so it's not updated with trade ticks.

        Parameters
        ----------
        tick : TradeTick
            The update tick.
        """
        # ADX requires OHLC data, so we don't update with trade ticks
        pass

    def _calculate_adx(self) -> None:
        """
        Calculate the Average Directional Index value.
        """
        # Calculate True Range (TR)
        if len(self.tr_values) == 0:
            tr = self.high_prices[-1] - self.low_prices[-1]
        else:
            prev_close = self.close_prices[-2]
            tr = max(
                self.high_prices[-1] - self.low_prices[-1],
                abs(self.high_prices[-1] - prev_close),
                abs(self.low_prices[-1] - prev_close)
            )

        self.tr_values = np.append(self.tr_values, tr)

        # Calculate Directional Movement (DM)
        if len(self.high_prices) > 1:
            high_diff = self.high_prices[-1] - self.high_prices[-2]
            low_diff = self.low_prices[-2] - self.low_prices[-1]

            plus_dm = max(0, high_diff) if high_diff > low_diff else 0
            minus_dm = max(0, low_diff) if low_diff > high_diff else 0

            self.plus_dm_values = np.append(self.plus_dm_values, plus_dm)
            self.minus_dm_values = np.append(self.minus_dm_values, minus_dm)

        # Calculate smoothed ATR, +DI, and -DI
        if len(self.tr_values) >= self.period:
            if len(self.atr_values) == 0:
                atr = np.mean(self.tr_values[-self.period:])
                plus_di = 100 * np.mean(self.plus_dm_values[-self.period:]) / atr if atr > 0 else 0
                minus_di = 100 * np.mean(self.minus_dm_values[-self.period:]) / atr if atr > 0 else 0
            else:
                atr = (self.atr_values[-1] * (self.period - 1) + self.tr_values[-1]) / self.period
                plus_di = (self.plus_di_values[-1] * (self.period - 1) + 100 * self.plus_dm_values[-1] / atr) / self.period if atr > 0 else 0
                minus_di = (self.minus_di_values[-1] * (self.period - 1) + 100 * self.minus_dm_values[-1] / atr) / self.period if atr > 0 else 0

            self.atr_values = np.append(self.atr_values, atr)
            self.plus_di_values = np.append(self.plus_di_values, plus_di)
            self.minus_di_values = np.append(self.minus_di_values, minus_di)

            # Calculate Directional Index (DX)
            di_diff = abs(plus_di - minus_di)
            di_sum = plus_di + minus_di
            dx = 100 * di_diff / di_sum if di_sum > 0 else 0

            self.dx_values = np.append(self.dx_values, dx)

            # Calculate ADX
            if len(self.dx_values) >= self.period:
                if len(self.adx_values) == 0:
                    adx = np.mean(self.dx_values[-self.period:])
                else:
                    adx = (self.adx_values[-1] * (self.period - 1) + dx) / self.period

                self.adx_values = np.append(self.adx_values, adx)

        # Keep only the needed values
        if len(self.tr_values) > self.period:
            self.tr_values = self.tr_values[-self.period:]
        if len(self.plus_dm_values) > self.period:
            self.plus_dm_values = self.plus_dm_values[-self.period:]
        if len(self.minus_dm_values) > self.period:
            self.minus_dm_values = self.minus_dm_values[-self.period:]
        if len(self.atr_values) > self.period:
            self.atr_values = self.atr_values[-self.period:]
        if len(self.plus_di_values) > self.period:
            self.plus_di_values = self.plus_di_values[-self.period:]
        if len(self.minus_di_values) > self.period:
            self.minus_di_values = self.minus_di_values[-self.period:]
        if len(self.dx_values) > self.period:
            self.dx_values = self.dx_values[-self.period:]
        if len(self.adx_values) > self.period:
            self.adx_values = self.adx_values[-self.period:]

    @property
    def value(self) -> Optional[float]:
        """
        Return the current ADX value.

        Returns
        -------
        Optional[float]
            The current value.
        """
        if len(self.adx_values) == 0:
            return None
        return self.adx_values[-1]

    @property
    def positive_directional_index(self) -> Optional[float]:
        """
        Return the current +DI value.

        Returns
        -------
        Optional[float]
            The current +DI value.
        """
        if len(self.plus_di_values) == 0:
            return None
        return self.plus_di_values[-1]

    @property
    def negative_directional_index(self) -> Optional[float]:
        """
        Return the current -DI value.

        Returns
        -------
        Optional[float]
            The current -DI value.
        """
        if len(self.minus_di_values) == 0:
            return None
        return self.minus_di_values[-1]

    @property
    def has_inputs(self) -> bool:
        """
        Return whether the indicator has inputs.

        Returns
        -------
        bool
            True if the indicator has inputs, False otherwise.
        """
        return len(self.high_prices) > 0

    @property
    def initialized(self) -> bool:
        """
        Return whether the indicator is initialized.

        Returns
        -------
        bool
            True if the indicator is initialized, False otherwise.
        """
        return self._initialized

    def reset(self) -> None:
        """
        Reset the indicator.
        """
        self.high_prices = np.array([])
        self.low_prices = np.array([])
        self.close_prices = np.array([])

        self.tr_values = np.array([])
        self.plus_dm_values = np.array([])
        self.minus_dm_values = np.array([])

        self.atr_values = np.array([])
        self.plus_di_values = np.array([])
        self.minus_di_values = np.array([])
        self.dx_values = np.array([])
        self.adx_values = np.array([])

        self._initialized = False
