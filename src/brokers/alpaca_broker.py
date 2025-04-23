import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
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

    async def place_order(self, side: str, size: float, price: float, symbol: str, order_type: str):
        """Place an order on Alpaca, branching between market and limit types."""
        # Convert string side into OrderSide enum
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        # Select order request based on type parameter
        if order_type.lower() == "market":
            order_req = MarketOrderRequest(
                symbol=symbol,
                qty=size,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )
        else:
            order_req = LimitOrderRequest(
                symbol=symbol,
                qty=size,
                limit_price=price,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )
        print(f"[AlpacaBroker] Placing order: {order_req}")
        # Submit the order to Alpaca and return the response
        return self.client.submit_order(order_data=order_req)