"""
Momentum Overlay Module for Market Maker Strategy.

This module contains the momentum detection and trading logic for the market maker strategy.
It identifies strong directional moves and generates signals for momentum-based trades.
"""

from decimal import Decimal
from typing import Dict, Optional, Tuple
import numpy as np


class MomentumOverlay:
    """
    Momentum detection and trading logic for market maker strategy.

    This class identifies strong directional moves in the market and
    generates signals for momentum-based trades.

    Parameters
    ----------
    rsi_threshold_high : float
        RSI threshold for detecting strong upward momentum
    rsi_threshold_low : float
        RSI threshold for detecting strong downward momentum
    bbands_entry_threshold : float
        Bollinger Bands threshold for momentum entry (in standard deviations)
    momentum_trade_size_multiplier : float
        Multiplier for trade size when taking momentum trades
    """

    def __init__(
        self,
        rsi_threshold_high: float = 70.0,
        rsi_threshold_low: float = 30.0,
        bbands_entry_threshold: float = 2.0,
        momentum_trade_size_multiplier: float = 2.0,
    ) -> None:
        self.rsi_threshold_high = rsi_threshold_high
        self.rsi_threshold_low = rsi_threshold_low
        self.bbands_entry_threshold = bbands_entry_threshold
        self.momentum_trade_size_multiplier = momentum_trade_size_multiplier
        
        # State variables
        self.last_momentum_signal = None
        self.active_momentum_trade = False
        self.momentum_entry_price = None
        self.momentum_direction = None  # 'LONG' or 'SHORT'
        
    def detect_momentum(
        self,
        rsi_value: float,
        price: Decimal,
        bbands_upper: Optional[Decimal],
        bbands_lower: Optional[Decimal],
        bbands_middle: Optional[Decimal],
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect momentum signals based on technical indicators.

        Parameters
        ----------
        rsi_value : float
            The current RSI value
        price : Decimal
            The current price
        bbands_upper : Decimal, optional
            The upper Bollinger Band value
        bbands_lower : Decimal, optional
            The lower Bollinger Band value
        bbands_middle : Decimal, optional
            The middle Bollinger Band value (SMA)

        Returns
        -------
        Tuple[bool, Optional[str]]
            A tuple containing (signal_detected, direction)
            where direction is 'LONG', 'SHORT', or None
        """
        # Check if we already have an active momentum trade
        if self.active_momentum_trade:
            return False, None
            
        # Check for strong momentum using RSI
        strong_uptrend = rsi_value is not None and rsi_value > self.rsi_threshold_high
        strong_downtrend = rsi_value is not None and rsi_value < self.rsi_threshold_low
        
        # Check for price breakouts using Bollinger Bands
        if bbands_upper is not None and bbands_lower is not None and bbands_middle is not None:
            # Calculate distance from middle band in terms of standard deviations
            band_width = (bbands_upper - bbands_lower) / 2
            if band_width > 0:
                distance_from_middle = abs(price - bbands_middle) / band_width
                
                # Check for breakout beyond threshold
                if distance_from_middle >= self.bbands_entry_threshold:
                    # Determine direction
                    if price > bbands_middle and strong_uptrend:
                        return True, 'LONG'
                    elif price < bbands_middle and strong_downtrend:
                        return True, 'SHORT'
        
        return False, None
        
    def calculate_momentum_trade_size(self, base_size: Decimal) -> Decimal:
        """
        Calculate the size for a momentum trade.

        Parameters
        ----------
        base_size : Decimal
            The base trade size

        Returns
        -------
        Decimal
            The calculated momentum trade size
        """
        return base_size * Decimal(str(self.momentum_trade_size_multiplier))
        
    def update_momentum_trade_status(
        self,
        price: Decimal,
        rsi_value: float,
        profit_take_pct: float,
    ) -> Tuple[bool, bool]:
        """
        Update the status of an active momentum trade and check for exit conditions.

        Parameters
        ----------
        price : Decimal
            The current price
        rsi_value : float
            The current RSI value
        profit_take_pct : float
            The profit target percentage

        Returns
        -------
        Tuple[bool, bool]
            A tuple containing (should_exit, is_profit)
            where is_profit indicates if the exit is due to profit target
        """
        if not self.active_momentum_trade or self.momentum_entry_price is None:
            return False, False
            
        # Calculate current profit/loss percentage
        if self.momentum_direction == 'LONG':
            pnl_pct = float((price - self.momentum_entry_price) / self.momentum_entry_price * 100)
            
            # Check for profit target
            if pnl_pct >= profit_take_pct:
                return True, True
                
            # Check for RSI reversal
            if rsi_value is not None and rsi_value < 50:
                return True, False
                
        elif self.momentum_direction == 'SHORT':
            pnl_pct = float((self.momentum_entry_price - price) / self.momentum_entry_price * 100)
            
            # Check for profit target
            if pnl_pct >= profit_take_pct:
                return True, True
                
            # Check for RSI reversal
            if rsi_value is not None and rsi_value > 50:
                return True, False
                
        return False, False
        
    def start_momentum_trade(self, direction: str, entry_price: Decimal) -> None:
        """
        Start a new momentum trade.

        Parameters
        ----------
        direction : str
            The direction of the trade ('LONG' or 'SHORT')
        entry_price : Decimal
            The entry price of the trade
        """
        self.active_momentum_trade = True
        self.momentum_direction = direction
        self.momentum_entry_price = entry_price
        self.last_momentum_signal = direction
        
    def end_momentum_trade(self) -> None:
        """
        End the current momentum trade.
        """
        self.active_momentum_trade = False
        self.momentum_direction = None
        self.momentum_entry_price = None
        
    def get_status(self) -> Dict:
        """
        Get the current status of the momentum overlay.

        Returns
        -------
        Dict
            Dictionary containing the current momentum status
        """
        return {
            "active_momentum_trade": self.active_momentum_trade,
            "momentum_direction": self.momentum_direction,
            "momentum_entry_price": self.momentum_entry_price,
            "last_momentum_signal": self.last_momentum_signal,
        }
