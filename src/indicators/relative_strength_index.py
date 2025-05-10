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
Implementation of a Relative Strength Index (RSI) indicator.
"""

from typing import Optional

import numpy as np

from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import PriceType


class RelativeStrengthIndex(Indicator):
    """
    A Relative Strength Index (RSI) indicator.
    
    The RSI is a momentum oscillator that measures the speed and change of price
    movements. It oscillates between 0 and 100 and is typically used to identify
    overbought or oversold conditions.
    
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
        super().__init__(bar_type)
        
        self.period = period
        self.price_type = price_type
        
        # Initialize arrays
        self.prices = np.array([])
        self.gains = np.array([])
        self.losses = np.array([])
        self.avg_gains = np.array([])
        self.avg_losses = np.array([])
        self.rsi_values = np.array([])
    
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
        
        # Calculate price changes if we have at least 2 prices
        if len(self.prices) > 1:
            # Calculate price change
            change = self.prices[-1] - self.prices[-2]
            
            # Calculate gain and loss
            gain = max(0, change)
            loss = max(0, -change)
            
            # Append to arrays
            self.gains = np.append(self.gains, gain)
            self.losses = np.append(self.losses, loss)
            
            # Calculate RSI if we have enough data
            if len(self.gains) >= self.period:
                self._calculate_rsi()
        
        # Keep only the needed prices
        if len(self.prices) > self.period + 1:
            self.prices = self.prices[-(self.period + 1):]
    
    def _calculate_rsi(self) -> None:
        """
        Calculate the Relative Strength Index value.
        """
        # Calculate average gain and loss
        if len(self.avg_gains) == 0:
            # First average is a simple average
            avg_gain = sum(self.gains[:self.period]) / self.period
            avg_loss = sum(self.losses[:self.period]) / self.period
        else:
            # Subsequent averages use the Wilder's smoothing method
            avg_gain = (self.avg_gains[-1] * (self.period - 1) + self.gains[-1]) / self.period
            avg_loss = (self.avg_losses[-1] * (self.period - 1) + self.losses[-1]) / self.period
        
        # Append to arrays
        self.avg_gains = np.append(self.avg_gains, avg_gain)
        self.avg_losses = np.append(self.avg_losses, avg_loss)
        
        # Calculate RS (Relative Strength)
        rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs)) if rs != float('inf') else 100
        
        # Append RSI to values
        self.rsi_values = np.append(self.rsi_values, rsi)
        
        # Keep only the needed values
        if len(self.avg_gains) > self.period:
            self.avg_gains = self.avg_gains[-self.period:]
        if len(self.avg_losses) > self.period:
            self.avg_losses = self.avg_losses[-self.period:]
        if len(self.rsi_values) > self.period:
            self.rsi_values = self.rsi_values[-self.period:]
    
    @property
    def value(self) -> Optional[float]:
        """
        Return the current indicator value.
        
        Returns
        -------
        Optional[float]
            The current value.
        """
        if len(self.rsi_values) == 0:
            return None
        return self.rsi_values[-1]
    
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
        self.gains = np.array([])
        self.losses = np.array([])
        self.avg_gains = np.array([])
        self.avg_losses = np.array([])
        self.rsi_values = np.array([])
