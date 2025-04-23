# ShadowBroker class for logging signals instead of placing orders
from src.brokers.base_broker import BaseBroker
import os
import httpx

class ShadowBroker(BaseBroker):
    """Broker that logs signals instead of placing orders."""
    def __init__(self, paper: bool = False, **kwargs):
        """
        Initialize ShadowBroker, loading Webhook URL from environment.
        Accept any broker parameters but ignore them for logging.
        """
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

        if not self.webhook_url:
            print("Warning: No Discord webhook URL configured; Discord notifications disabled")

    async def place_order(
        self,
        side: str,
        size: float,
        price: float,
        symbol: str,
        order_type: str = "limit"
    ):
        """Log shadow order signals; 'order_type' parameter is accepted but ignored."""
        message = f"Shadow Signal -> {side} {size} @ {price} ({symbol})"
        print(message)
        if self.webhook_url:
            payload = {"content": message}
            async with httpx.AsyncClient() as client:
                await client.post(self.webhook_url, json=payload)
        return None 