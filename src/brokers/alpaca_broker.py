import os
from alpaca.trading.client import TradingClient
from src.brokers.base_broker import BaseBroker

class AlpacaBroker(BaseBroker):
    """Broker wrapper for Alpaca Trading API."""
    def __init__(self, paper: bool = True):
        """Initialize AlpacaBroker, loading API credentials from environment."""
        api_key = os.getenv('APCA_API_KEY_ID')
        api_secret = os.getenv('APCA_API_SECRET_KEY')
        
        if not api_key or not api_secret:
            raise ValueError("API credentials not found in environment variables")
        self.client = TradingClient(api_key, api_secret, paper=paper)

    async def place_order(self, side: str, size: float, price: float, symbol: str):
        """Place a limit order on Alpaca (async for interface consistency)."""
        order = self.client.submit_order(
            symbol=symbol,
            side=side.lower(),
            type="limit",
            qty=size,
            limit_price=price,
            time_in_force="day"
        )
        return order