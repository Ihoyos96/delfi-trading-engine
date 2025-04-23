# AlpacaDataProvider for real-time data
import os
import json
import redis
from src.data_providers.base_data_provider import BaseDataProvider
from alpaca.data.live import StockDataStream
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
import pandas as pd
from datetime import datetime
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
import subprocess
import threading
import pathlib
import asyncio
import time  # for warm-up delay
import atexit

class AlpacaDataProvider(BaseDataProvider):
    """Data provider using Alpaca-py for real-time and historical bars."""

    # Supports 1-second bars via Alpaca Order Streaming Aggregator and minute-bars via Alpaca
    supported_live_timeframes: list[str] = ['1S', '1Min']
    # List of timeframes this provider supports for historical data
    supported_historical_timeframes: list[str] = ['1Min', '5Min', '15Min', '1H', '1D']
    
    def __init__(self, **kwargs):
        """Initialize AlpacaDataProvider by loading credentials from env and building aggregator if needed."""
        print("[DataProvider] Initialized AlpacaDataProvider")
        api_key = os.getenv('APCA_API_KEY_ID')
        api_secret = os.getenv('APCA_API_SECRET_KEY')
        if not api_key or not api_secret:
            raise ValueError("Alpaca API credentials not found in environment variables")
        # real-time stream client
        self.stream = StockDataStream(api_key, api_secret)
        # historical data client
        self.hist_client = StockHistoricalDataClient(api_key, api_secret)
        # Redis publisher for external aggregators
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis = redis.Redis.from_url(redis_url)
        # Track if Redis was started by this provider and register cleanup
        self._redis_started = False
        atexit.register(self._shutdown_redis)
        # Track Rust aggregator processes per symbol
        self._aggregators = {}
        # Ensure Rust bar_aggregator binary exists or build it
        bin_env = os.getenv('AGGREGATOR_BIN')
        if bin_env and pathlib.Path(bin_env).is_file():
            self.aggregator_bin = bin_env
        else:
            # default aggregator path relative to this file
            base = pathlib.Path(__file__).parent.parent.parent / 'aggregator'
            release_bin = base / 'target' / 'release' / 'bar_aggregator'
            if not release_bin.is_file():
                # build in release mode
                subprocess.run(['cargo', 'build', '--release'], cwd=str(base), check=True)
            self.aggregator_bin = str(release_bin)

    def subscribe_bars(self, handler, symbol: str, timeframe: str):
        # Dispatch based on timeframe
        match timeframe:
            case '1S':
                # Ensure Redis server is running; start it if necessary
                try:
                    self.redis.ping()
                    print("[DataProvider] Redis is running.")
                except redis.exceptions.ConnectionError:
                    print("[DataProvider] Redis not running; launching redis-server...")
                    subprocess.Popen(['redis-server', '--daemonize', 'yes'])
                    time.sleep(1)
                    self._redis_started = True
                # launch external Rust aggregator
                if symbol not in self._aggregators:
                    env = os.environ.copy()
                    env['SYMBOL'] = symbol
                    # spawn without silencing stdout/stderr so we can see aggregator logs
                    proc = subprocess.Popen(
                        [self.aggregator_bin, '--symbol', symbol],
                        env=env
                    )
                    print(f"[DataProvider] Launched Rust aggregator (no redirection) PID {proc.pid} for symbol {symbol}")
                    time.sleep(2)  # warm-up delay to allow aggregator to connect
                    self._aggregators[symbol] = proc
                # subscribe to pre-aggregated 1s bars from Redis
                channel = f"bars:{symbol}"
                pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(channel)
                print(f"[DataProvider] Subscribed Redis pubsub to channel: {channel}")
                def _listener():
                    print(f"[DataProvider] Redis listener thread started for channel: {channel}")
                    for message in pubsub.listen():
                        if message and message['type'] == 'message':
                            print(f"[DataProvider] Raw Redis message: {message['data']}")
                            data = json.loads(message['data'])
                            tick = {
                                'open': data['open'],
                                'high': data['high'],
                                'low': data['low'],
                                'close': data['close'],
                                'volume': data['volume'],
                            }
                            result = handler(tick)
                            if asyncio.iscoroutine(result):
                                asyncio.run(result)
                threading.Thread(target=_listener, daemon=True).start()
            case '1Min':
                # wrap async handler so that coroutine callbacks are executed
                tf_enum = TimeFrame(1, TimeFrame.Minute)
                def _listener_min(bar):
                    result = handler(bar)
                    if asyncio.iscoroutine(result):
                        asyncio.run(result)
                self.stream.subscribe_bars(_listener_min, symbol)
            case _:
                raise ValueError(f"Unsupported timeframe: {timeframe}")

    def run(self):
        """Kick off the live data stream."""
        print("[DataProvider] Calling run() to start AlpacaDataStream")
        self.stream.run()

    def stop(self):
        """Stop streaming (no-op if not supported by Alpaca-py)."""
        # terminate any running Rust aggregator processes
        for proc in self._aggregators.values():
            try:
                proc.terminate()
            except Exception:
                pass
        self._aggregators.clear()
        # note: Alpaca stream has no explicit stop
        pass

    def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> pd.DataFrame:
        """
        Fetch historical bars using Alpaca-py StockHistoricalDataClient.
        """
        # Determine TimeFrame enum via switch
        match timeframe:
            case '1Min':
                tf_enum = TimeFrame(1, TimeFrameUnit.Minute)
            case '5Min':
                tf_enum = TimeFrame(5, TimeFrameUnit.Minute)
            case '15Min':
                tf_enum = TimeFrame(15, TimeFrameUnit.Minute)
            case '1H':
                tf_enum = TimeFrame(1, TimeFrameUnit.Hour)
            case '1D':
                tf_enum = TimeFrame(1, TimeFrameUnit.Day)
            case _:
                raise ValueError(f"Unsupported timeframe: {timeframe}")
        # Build request
        print(f"[DataProvider] Fetching historical bars for {symbol} from {start} to {end} with timeframe {tf_enum.value}")
        req = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=tf_enum,
            start=start,
            end=end,
            limit=100000
        )
        bars = self.hist_client.get_stock_bars(req)
        df = bars.df
        # flatten MultiIndex
        if isinstance(df.index, pd.MultiIndex):
            df.index = df.index.get_level_values(1)
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df[['open', 'high', 'low', 'close', 'volume']]

    def subscribe_trades(self, handler, symbol: str):
        """Subscribe to real-time trade stream for the given symbol."""
        # wrap handler to also publish raw trades to Redis for microservice aggregation
        def _wrapped(trade):
            # publish raw trade event
            payload = {
                'symbol': symbol,
                'timestamp': trade.timestamp.isoformat(),
                'price': trade.price,
                'size': trade.size
            }
            self.redis.publish(f"trades:{symbol}", json.dumps(payload))
            # call user handler
            handler(trade)

        self.stream.subscribe_trades(_wrapped, symbol)

    def subscribe_quotes(self, handler, symbol: str):
        """Subscribe to real-time quote stream (bid/ask) for the given symbol."""
        # wrap handler to also publish raw quotes to Redis
        def _wrapped(q):
            payload = {
                'symbol': symbol,
                'timestamp': q.timestamp.isoformat(),
                'bid_price': q.bid_price,
                'bid_size': q.bid_size,
                'ask_price': q.ask_price,
                'ask_size': q.ask_size
            }
            self.redis.publish(f"quotes:{symbol}", json.dumps(payload))
            handler(q)

        self.stream.subscribe_quotes(_wrapped, symbol)

    def _shutdown_redis(self):
        """Shutdown Redis if it was started by this provider."""
        if getattr(self, '_redis_started', False):
            print("[DataProvider] Shutting down Redis...")
            try:
                subprocess.run(['redis-cli', 'shutdown'], check=False)
            except Exception:
                pass 