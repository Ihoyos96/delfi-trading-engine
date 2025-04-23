from collections import deque
from typing import Any, Dict

from src.backtester.backtester import Backtester
from src.strategies.base_strategy import BaseStrategy

class EMACrossoverStrategy(BaseStrategy):
    """
    EMA Crossover Strategy encapsulating both backtest and live execution logic.
    """

    def __init__(self, params, broker: Any = None, data_provider: Any = None) -> None:
        super().__init__(params, broker, data_provider)
        self.short_window = params.short_window
        self.long_window = params.long_window
        self.prices = deque(maxlen=self.long_window)
        # EMA state
        self.short_ema = None
        self.long_ema = None
        self.position = 0  # 0=no position, 1=long, -1=short

    async def on_start(self) -> None:
        """Initialize EMA state and clear buffers."""
        self.prices.clear()
        self.short_ema = None
        self.long_ema = None
        self.position = 0

    async def on_new_tick(self, tick: Dict[str, Any]) -> None:
        """Process each incoming tick/bar, update EMAs, and send orders on crossovers."""
        price = tick.get("close")
        if price is None:
            return
        self.prices.append(price)

        # Not enough data yet
        if len(self.prices) < self.long_window:
            return

        # Compute or update EMAs
        alpha_s = 2 / (self.short_window + 1)
        alpha_l = 2 / (self.long_window + 1)
        if self.short_ema is None:
            # initialize EMAs at first full window
            self.short_ema = price
            self.long_ema = price
        else:
            self.short_ema = alpha_s * price + (1 - alpha_s) * self.short_ema
            self.long_ema = alpha_l * price + (1 - alpha_l) * self.long_ema

        # Crossover logic
        if self.short_ema > self.long_ema and self.position <= 0:
            # Enter long
            size = self.params.dict().get("size", 1)
            await self.broker.place_order("BUY", size=size, price=price)
            self.position = 1

        elif self.short_ema < self.long_ema and self.position >= 0:
            # Enter short
            size = self.params.dict().get("size", 1)
            await self.broker.place_order("SELL", size=size, price=price)
            self.position = -1

    async def on_stop(self) -> None:
        """Cleanup if needed when strategy stops."""
        # e.g., close remaining positions
        pass

    def run(self) -> None:
        """
        Execute the strategy live using the pre-assigned broker and data provider.
        """
        import asyncio
        print(f"Starting EMA Crossover live run with params: {self.params}")
        # initialize state
        asyncio.run(self.on_start())

        # handler to wrap incoming bars into on_new_tick
        async def _handle_bar(bar):
            tick = {
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': float(bar.volume)
            }
            await self.on_new_tick(tick)

        # subscribe to real-time bar stream
        self.data_provider.subscribe_bars(_handle_bar, self.params.symbol, self.params.timeframe)

        # start streaming; run blocks until interrupted
        try:
            self.data_provider.run()
        except KeyboardInterrupt:
            print("Stopping live data stream")
        finally:
            asyncio.run(self.on_stop())

    def backtest(self) -> dict:
        """
        Run a historical backtest using the backtester infrastructure.
        """

        # Verify provider is set
        if not self.data_provider:
            raise ValueError("Data provider not set")

        # Initialize and run backtester
        bt = Backtester(
            self.__class__,
            self.params,
            self.data_provider
        )
        return bt.run(
            self.params.symbol,
            self.params.period.start,
            self.params.period.end,
            self.params.timeframe
        ) 