from src.data_providers.alpaca_data_provider import AlpacaDataProvider

# Single source of truth for all data providers
DATA_PROVIDER_CONFIG = {
    "alpaca": {
        "display_name": "Alpaca Data Provider",
        "provider_class": AlpacaDataProvider,
        "config_model": None
    },
    # Future providers can be added here
} 