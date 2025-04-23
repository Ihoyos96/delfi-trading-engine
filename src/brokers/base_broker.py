# BaseBroker abstract class
from abc import ABC, abstractmethod

class BaseBroker(ABC):
    """Abstract base class for all brokers."""

    @abstractmethod
    async def place_order(
        self,
        side: str,
        size: float,
        price: float,
        symbol: str,
        order_type: str = "market"
    ):
        """Place an order with side, size, price, symbol, and order type (defaulting to market)."""
        pass