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
from typing import Any, Dict, Optional

from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import PriceType

# Try to import pandas_ta
try:
    import pandas_ta as ta
except ImportError:
    raise ImportError(
        "pandas_ta is not installed. Please install it with: pip install pandas-ta"
    )


class PandasTaIndicator(Indicator):
    """
    Generic indicator implementation using pandas-ta.

    This class allows using any indicator from the pandas-ta library with Nautilus Trader.

    Parameters
    ----------
    bar_type : BarType
        The bar type for the indicator.
    indicator_name : str
        The name of the indicator function to use (e.g., 'rsi', 'sma', 'ema', 'adx').
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
        self.indicator_name = indicator_name.lower()  # Normalize to lowercase
        self.indicator_params = params or {}
        self.price_type = price_type
        self.output_index = output_index

        # Get the period parameter if it exists
        self.period = self.indicator_params.get("length", 14)

        # Initialize data storage
        self.prices = np.array([])
        self.high_prices = np.array([])
        self.low_prices = np.array([])
        self.open_prices = np.array([])
        self.volume = np.array([])
        self.indicator_values = np.array([])

        # For multi-output indicators
        self.additional_values = {}

        # Determine if indicator needs OHLCV data
        # This is a heuristic based on common indicators that need more than just close prices
        self._determine_data_needs()

    def _determine_data_needs(self) -> None:
        """
        Determine what data the indicator needs based on its name and parameters.
        """
        # Some indicators are known to need OHLCV data
        known_ohlcv_indicators = [
            'adx', 'atr', 'bbands', 'donchian', 'kc', 'macd', 'supertrend', 'vwap',
            'ad', 'adosc', 'aobv', 'cmf', 'efi', 'eom', 'mfi', 'obv', 'pvol', 'pvt'
        ]

        if self.indicator_name.lower() in known_ohlcv_indicators:
            self.needs_ohlcv = True
            return

        # Check if the indicator function exists in pandas_ta
        try:
            indicator_func = getattr(ta, self.indicator_name)
            # Get the function signature
            import inspect
            sig = inspect.signature(indicator_func)
            params = list(sig.parameters.keys())

            # Most indicators that need OHLCV have high, low parameters
            self.needs_ohlcv = any(param in params for param in ['high', 'low', 'open', 'volume'])
        except (AttributeError, TypeError):
            # If we can't determine, assume it only needs close prices
            self.needs_ohlcv = False

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

        # For indicators that need OHLCV data
        if self.needs_ohlcv:
            # Extract OHLCV data
            open_price = bar.open.as_double()
            high = bar.high.as_double()
            low = bar.low.as_double()
            volume = float(bar.volume)

            # Append to arrays
            self.open_prices = np.append(self.open_prices, open_price)
            self.high_prices = np.append(self.high_prices, high)
            self.low_prices = np.append(self.low_prices, low)
            self.volume = np.append(self.volume, volume)

            # Keep only the needed data
            if len(self.high_prices) > self.period * 3:  # Keep 3x the period for safety
                self.open_prices = self.open_prices[-(self.period * 3):]
                self.high_prices = self.high_prices[-(self.period * 3):]
                self.low_prices = self.low_prices[-(self.period * 3):]
                self.volume = self.volume[-(self.period * 3):]

        # Calculate indicator if we have enough data
        if len(self.prices) >= self.period:
            # Create a DataFrame for pandas-ta
            if self.needs_ohlcv:
                # Make sure all arrays have the same length
                min_length = min(len(self.prices), len(self.open_prices), len(self.high_prices),
                                len(self.low_prices), len(self.volume))

                # Create OHLCV DataFrame with arrays of the same length
                df = pd.DataFrame({
                    'open': self.open_prices[-min_length:],
                    'high': self.high_prices[-min_length:],
                    'low': self.low_prices[-min_length:],
                    'close': self.prices[-min_length:],
                    'volume': self.volume[-min_length:]
                })
            else:
                # Create a simple DataFrame with just close prices
                df = pd.DataFrame({'close': self.prices})

            # Calculate the indicator using pandas-ta
            result = self._calculate_indicator(df)

            # Add the result to our values
            if result is not None:
                self.indicator_values = np.append(self.indicator_values, result)

        # Keep only the needed prices
        if len(self.prices) > self.period * 3:  # Keep 3x the period for safety
            self.prices = self.prices[-(self.period * 3):]

        # Keep only the needed indicator values
        if len(self.indicator_values) > self.period:
            self.indicator_values = self.indicator_values[-self.period:]

    def _calculate_indicator(self, df: pd.DataFrame) -> Optional[float]:
        """
        Calculate the indicator using pandas-ta.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with price data.

        Returns
        -------
        Optional[float]
            The indicator value, or None if calculation failed.
        """
        try:
            # Get the indicator function from pandas-ta
            indicator_func = getattr(ta, self.indicator_name)

            # Call the function with the appropriate parameters
            if self.needs_ohlcv:
                # For OHLCV indicators, check the function signature to determine how to call it
                import inspect
                sig = inspect.signature(indicator_func)
                params = list(sig.parameters.keys())

                if 'high' in params and 'low' in params and 'close' in params:
                    # For indicators that need high, low, close (like ADX)
                    result = indicator_func(df.high, df.low, df.close, **self.indicator_params)
                elif 'open' in params and 'high' in params and 'low' in params and 'close' in params:
                    # For indicators that need open, high, low, close
                    result = indicator_func(df.open, df.high, df.low, df.close, **self.indicator_params)
                elif 'high' in params and 'low' in params and 'close' in params and 'volume' in params:
                    # For indicators that need high, low, close, volume
                    result = indicator_func(df.high, df.low, df.close, df.volume, **self.indicator_params)
                elif 'open' in params and 'high' in params and 'low' in params and 'close' in params and 'volume' in params:
                    # For indicators that need all OHLCV
                    result = indicator_func(df.open, df.high, df.low, df.close, df.volume, **self.indicator_params)
                else:
                    # For other indicators, pass the DataFrame directly
                    result = indicator_func(df, **self.indicator_params)
            else:
                # For price-only indicators, pass the close series
                result = indicator_func(df.close, **self.indicator_params)

            # Handle different return types
            if isinstance(result, pd.Series):
                # Store the result in additional_values for potential access
                self.additional_values['main'] = result.iloc[-1] if not result.empty else None
                return result.iloc[-1] if not result.empty else None

            elif isinstance(result, pd.DataFrame):
                # For multi-output indicators, store all columns
                for col in result.columns:
                    self.additional_values[col] = result[col].iloc[-1] if not result.empty else None

                # Return the specified output index or the first column
                if self.output_index < len(result.columns):
                    col_name = result.columns[self.output_index]
                    return result[col_name].iloc[-1] if not result.empty else None
                else:
                    # Default to first column if output_index is out of range
                    col_name = result.columns[0]
                    return result[col_name].iloc[-1] if not result.empty else None
            else:
                return None

        except Exception as e:
            print(f"Error in _calculate_indicator: {e}")
            return None

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

    @property
    def initialized(self) -> bool:
        """
        Return whether the indicator is initialized.

        Returns
        -------
        bool
            True if the indicator has values, else False.
        """
        return len(self.indicator_values) > 0

    def reset(self) -> None:
        """
        Reset the indicator.
        """
        self.prices = np.array([])
        self.high_prices = np.array([])
        self.low_prices = np.array([])
        self.open_prices = np.array([])
        self.volume = np.array([])
        self.indicator_values = np.array([])
        self.additional_values = {}
