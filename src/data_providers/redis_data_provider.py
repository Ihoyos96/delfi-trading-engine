from abc import abstractmethod
import os
import json
import redis
import pandas as pd
from datetime import datetime

from src.data_providers.base_data_provider import BaseDataProvider
from src.data_providers.alpaca_data_provider import AlpacaDataProvider

class RedisBarProvider(BaseDataProvider):
    """Data provider that consumes 1-second bars from Redis and delegates historical calls to Alpaca."""

    def __init__(self, **kwargs):
        # Setup Redis pub/sub
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis = redis.Redis.from_url(redis_url)
        # ignore the initial subscription confirmation messages
        self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
        # Fallback provider for history, trades, quotes
        self.fallback = AlpacaDataProvider()

    def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str
    ) -> pd.DataFrame:
        # Delegate historical fetch to AlpacaDataProvider
        return self.fallback.get_historical_bars(symbol, start, end, timeframe)

    def subscribe_bars(self, handler, symbol: str, timeframe: str):
        # Subscribe to the Redis channel for pre-aggregated 1-second bars
        channel = f"bars:{symbol}"
        def _handler(message):
            data = json.loads(message['data'])
            tick = {
                'open': data['open'],
                'high': data['high'],
                'low': data['low'],
                'close': data['close'],
                'volume': data['volume'],
            }
            handler(tick)
        self.pubsub.subscribe(**{channel: _handler})

    def run(self):
        # Block and dispatch bars to handler via callback
        for message in self.pubsub.listen():
            # handlers are invoked automatically by redis client
            pass

    def stop(self):
        self.pubsub.close()

    def subscribe_trades(self, handler, symbol: str):
        # Delegate trades subscription
        return self.fallback.subscribe_trades(handler, symbol)

    def subscribe_quotes(self, handler, symbol: str):
        # Delegate quotes subscription
        return self.fallback.subscribe_quotes(handler, symbol) 