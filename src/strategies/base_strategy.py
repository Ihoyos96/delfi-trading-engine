from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseStrategy(ABC):
    """Abstract base class defining the interface for all trading strategies."""

    # Execution broker (e.g., AlpacaBroker, SimulatedBroker, or LoggingBroker)
    broker: Any = None

    # Data provider (e.g., AlpacaDataProvider, HistoricalFetcher)
    data_provider: Any = None

    def __init__(self, params: Any, broker: Any = None, data_provider: Any = None) -> None:
        """Initialize the strategy with its parameter model and optional broker."""
        self.params = params
        # Execution broker (set during init)
        self.broker = broker
        # Data provider (set during init)
        self.data_provider = data_provider

    def run(self) -> None:
        """
        Execute the strategy in live mode using the pre-assigned broker.
        If shadow_mode=True, broker should log signals instead of executing orders.
        """
        raise NotImplementedError

    def backtest(self) -> dict:
        """
        Execute full backtest for this strategy using historical data.
        Returns performance metrics as a dict.
        """
        raise NotImplementedError
