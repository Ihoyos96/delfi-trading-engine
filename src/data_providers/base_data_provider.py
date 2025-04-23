# BaseDataProvider and AlpacaDataProvider for real-time data
from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime


class BaseDataProvider(ABC):
    """Abstract base class for all data providers."""

    # List of timeframe strings this provider supports for live streaming
    supported_live_timeframes: list[str] = []
    # List of timeframe strings this provider supports for historical data
    supported_historical_timeframes: list[str] = []

    @abstractmethod
    def subscribe_bars(self, handler, symbol: str, timeframe: str):
        """Subscribe to a real-time bar stream for the given symbol and timeframe."""
        pass

    @abstractmethod
    def run(self):
        """Start the data stream loop."""
        pass

    @abstractmethod
    def stop(self):
        """Stop the data stream loop."""
        pass

    @abstractmethod
    def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str
    ) -> pd.DataFrame:
        """Fetch historical bars for backtesting."""
        pass

    @abstractmethod
    def subscribe_trades(self, handler, symbol: str):
        """Subscribe to real-time trade events for the given symbol."""
        pass

    @abstractmethod
    def subscribe_quotes(self, handler, symbol: str):
        """Subscribe to real-time quote (top-of-book) events for the given symbol."""
        pass