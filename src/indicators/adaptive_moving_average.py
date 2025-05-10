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
Implementation of an Adaptive Moving Average (AMA) indicator.
"""

from typing import Optional

import numpy as np

from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import PriceType


class AdaptiveMovingAverage(Indicator):
    """
    An Adaptive Moving Average (AMA) indicator.
    
    The AMA adjusts its smoothing factor based on market volatility, making it
    more responsive to price changes in trending markets and less responsive in
    ranging markets.
    
    Parameters
    ----------
    bar_type : BarType
        The bar type for the indicator.
    period : int
        The period for the indicator (number of bars).
    fast_period : int
        The fast EMA period (default: 2).
    slow_period : int
        The slow EMA period (default: 30).
    price_type : PriceType
        The price type for the indicator (default: PriceType.LAST).
    """
    
    def __init__(
        self,
        bar_type: BarType,
        period: int,
        fast_period: int = 2,
        slow_period: int = 30,
        price_type: PriceType = PriceType.LAST,
    ):
        super().__init__(bar_type)
        
        self.period = period
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.price_type = price_type
        
        # Initialize arrays
        self.prices = np.array([])
        self.values = np.array([])
        
        # Fast and slow smoothing constants
        self.fast_sc = 2.0 / (self.fast_period + 1.0)
        self.slow_sc = 2.0 / (self.slow_period + 1.0)
    
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
        
        # Keep only the needed prices
        if len(self.prices) > self.period + 1:
            self.prices = self.prices[-(self.period + 1):]
        
        # Calculate AMA if we have enough data
        if len(self.prices) > self.period:
            self._calculate_ama()
        else:
            # Not enough data yet, use price as value
            self.values = np.append(self.values, price)
    
    def _calculate_ama(self) -> None:
        """
        Calculate the Adaptive Moving Average value.
        """
        # Calculate direction (current price - price 'period' bars ago)
        direction = abs(self.prices[-1] - self.prices[0])
        
        # Calculate volatility (sum of absolute price changes over 'period' bars)
        volatility = sum(abs(self.prices[i] - self.prices[i-1]) for i in range(1, len(self.prices)))
        
        # Calculate efficiency ratio (ER)
        er = direction / volatility if volatility != 0 else 0
        
        # Calculate smoothing constant (SC)
        sc = (er * (self.fast_sc - self.slow_sc) + self.slow_sc) ** 2
        
        # Calculate AMA
        if len(self.values) == 0:
            # First value is just the price
            ama = self.prices[-1]
        else:
            # AMA = Previous AMA + SC * (Price - Previous AMA)
            ama = self.values[-1] + sc * (self.prices[-1] - self.values[-1])
        
        # Append AMA to values
        self.values = np.append(self.values, ama)
        
        # Keep only the needed values
        if len(self.values) > self.period:
            self.values = self.values[-self.period:]
    
    @property
    def value(self) -> Optional[float]:
        """
        Return the current indicator value.
        
        Returns
        -------
        Optional[float]
            The current value.
        """
        if len(self.values) == 0:
            return None
        return self.values[-1]
    
    @property
    def has_inputs(self) -> bool:
        """
        Return a value indicating whether the indicator has inputs.
        
        Returns
        -------
        bool
            True if the indicator has inputs, otherwise False.
        """
        return len(self.prices) > 0
    
    def reset(self) -> None:
        """
        Reset the indicator.
        """
        self.prices = np.array([])
        self.values = np.array([])
