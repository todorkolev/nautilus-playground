"""
Risk Manager Module for Market Maker Strategy.

This module contains the risk management logic for the market maker strategy.
It handles stop-loss, drawdown protection, and strategy shutdown functionality.
"""

from decimal import Decimal
from typing import Dict, Optional
import pandas as pd


class RiskManager:
    """
    Risk management for market maker strategy.

    This class handles risk management functions such as stop-loss,
    drawdown protection, and strategy shutdown.

    Parameters
    ----------
    max_drawdown_pct : float
        Maximum allowed drawdown as a percentage before shutdown
    stop_loss_pct : float
        Stop loss percentage for individual positions
    cooldown_minutes : int
        Cooldown period in minutes after a shutdown before resuming
    """

    def __init__(
        self,
        max_drawdown_pct: float = 5.0,
        stop_loss_pct: float = 1.0,
        cooldown_minutes: int = 60,
    ) -> None:
        self.max_drawdown_pct = max_drawdown_pct
        self.stop_loss_pct = stop_loss_pct
        self.cooldown_minutes = cooldown_minutes
        
        # State variables
        self.is_shutdown = False
        self.shutdown_time = None
        self.peak_equity = None
        self.current_equity = None
        self.current_drawdown_pct = 0.0
        
    def update_equity(self, equity: Decimal) -> None:
        """
        Update the current equity value and calculate drawdown.

        Parameters
        ----------
        equity : Decimal
            The current equity value
        """
        self.current_equity = equity
        
        # Initialize peak equity if not set
        if self.peak_equity is None:
            self.peak_equity = equity
        elif equity > self.peak_equity:
            self.peak_equity = equity
            
        # Calculate current drawdown
        if self.peak_equity > 0:
            self.current_drawdown_pct = float((self.peak_equity - equity) / self.peak_equity * 100)
        else:
            self.current_drawdown_pct = 0.0
            
    def check_shutdown_condition(self, current_time: pd.Timestamp) -> bool:
        """
        Check if the strategy should be shut down due to excessive drawdown.

        Parameters
        ----------
        current_time : pd.Timestamp
            The current time

        Returns
        -------
        bool
            True if the strategy should be shut down, False otherwise
        """
        # If already in shutdown, check if cooldown period has elapsed
        if self.is_shutdown:
            if self.shutdown_time is not None:
                elapsed_minutes = (current_time - self.shutdown_time).total_seconds() / 60
                if elapsed_minutes >= self.cooldown_minutes:
                    # Cooldown period has elapsed, can resume if drawdown is acceptable
                    if self.current_drawdown_pct < self.max_drawdown_pct * 0.7:  # Resume at 70% of max
                        self.is_shutdown = False
                        return False
                    else:
                        # Still in excessive drawdown, remain shutdown
                        return True
                else:
                    # Still in cooldown period
                    return True
        
        # Check if drawdown exceeds maximum allowed
        if self.current_drawdown_pct >= self.max_drawdown_pct:
            self.is_shutdown = True
            self.shutdown_time = current_time
            return True
            
        return False
        
    def check_position_stop_loss(
        self, 
        entry_price: Decimal, 
        current_price: Decimal, 
        position_side: str
    ) -> bool:
        """
        Check if a position has hit its stop loss level.

        Parameters
        ----------
        entry_price : Decimal
            The entry price of the position
        current_price : Decimal
            The current price
        position_side : str
            The side of the position ('LONG' or 'SHORT')

        Returns
        -------
        bool
            True if the stop loss has been hit, False otherwise
        """
        if entry_price <= 0 or current_price <= 0:
            return False
            
        stop_loss_threshold = Decimal(str(self.stop_loss_pct))
        
        if position_side == 'LONG':
            # For long positions, stop loss is hit if price falls below entry - threshold
            loss_pct = (entry_price - current_price) / entry_price
            return loss_pct >= stop_loss_threshold
        elif position_side == 'SHORT':
            # For short positions, stop loss is hit if price rises above entry + threshold
            loss_pct = (current_price - entry_price) / entry_price
            return loss_pct >= stop_loss_threshold
            
        return False
        
    def get_status(self) -> Dict:
        """
        Get the current status of the risk manager.

        Returns
        -------
        Dict
            Dictionary containing the current risk management status
        """
        return {
            "is_shutdown": self.is_shutdown,
            "shutdown_time": self.shutdown_time,
            "peak_equity": self.peak_equity,
            "current_equity": self.current_equity,
            "current_drawdown_pct": self.current_drawdown_pct,
        }
