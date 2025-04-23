from src.brokers.alpaca_broker import AlpacaBroker
from src.brokers.shadow_broker import ShadowBroker

# Single source of truth for all brokers
BROKER_CONFIG = {
    "alpaca": {
        "display_name": "Alpaca Broker",
        "broker_class": AlpacaBroker,
        "config_model": None  # no extra Pydantic model
    }
    # Future brokers can be added here
} 