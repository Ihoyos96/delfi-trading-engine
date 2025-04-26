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
    
    def on_start(self) -> None:
        """Perform any setup required for the strategy"""
        raise NotImplementedError
    
    def on_stop(self) -> None:
        """Perform any cleanup required after the strategy has stopped"""
        raise NotImplementedError

    def on_new_data(self, data: Dict[str, Any]) -> None:
        """
        Handle incoming market data
        Implement the broker logic here to perform trading operations
        """
        raise NotImplementedError

    def run(self) -> None:
        """
        Orchestrate the data provider to feed data to the on_new_data method.
        """
        raise NotImplementedError
