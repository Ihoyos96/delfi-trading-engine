# BaseBroker abstract class
from abc import ABC, abstractmethod

class BaseBroker(ABC):
    """Abstract base class for all brokers."""

    @abstractmethod
    async def get_account(self):
        """Get account details."""
        raise NotImplementedError

    @abstractmethod
    async def get_all_positions(self):
        """Get all positions."""
        raise NotImplementedError

    async def get_orders(self, status: str = "open", side: str = "sell"):
        """Get orders with given status (open, closed, all) and side (buy, sell)."""
        raise NotImplementedError

    @abstractmethod
    async def place_order(
        self,
        side: str,
        size: float,
        price: float,
        symbol: str,
        order_type: str = "market"
    ):
        """Place an order with side, size, price, symbol, and order type (market or limit, defaulting to market)."""
        raise NotImplementedError