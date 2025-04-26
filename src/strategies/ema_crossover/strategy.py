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

    def _get_order_type(self, price: float) -> str:
        """
        Dynamically choose order type based on EMA spread.
        Use market if difference between short and long EMA exceeds 0.1% of price,
        otherwise use limit order.
        """
        if self.short_ema is None or self.long_ema is None:
            return "market"
        spread = abs(self.short_ema - self.long_ema)
        # threshold = 0.1% of price
        if spread > 0.001 * price:
            return "market"
        return "limit"

    async def on_new_data(self, bar: Dict[str, Any]) -> None:
        """Handle incoming market data"""
        print(f"[EMACrossoverStrategy] Processing bar: {bar}")
        price = bar.get("close")
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
            # Enter long: strategy decides order type
            size = self.params.dict().get("size", 1)
            order_type = self._get_order_type(price)
            # Round price to penny for limit orders
            price_to_submit = round(price, 2) if order_type == "limit" else price
            await self.broker.place_order(
                side="BUY",
                size=size,
                price=price_to_submit,
                symbol=self.params.symbol,
                order_type=order_type
            )
            self.position = 1

        elif self.short_ema < self.long_ema and self.position >= 0:
            # Enter short: strategy decides order type
            size = self.params.dict().get("size", 1)
            order_type = self._get_order_type(price)
            # Round price to penny for limit orders
            price_to_submit = round(price, 2) if order_type == "limit" else price
            await self.broker.place_order(
                side="SELL",
                size=size,
                price=price_to_submit,
                symbol=self.params.symbol,
                order_type=order_type
            )
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
        print(f"[EMACrossoverStrategy] Starting EMA Crossover live run with params: {self.params}")
        # initialize state
        asyncio.run(self.on_start())

        # handler to wrap incoming bars into on_new_data
        async def _handle_bar(bar):
            # bar comes in as a dict from Redis provider
            await self.on_new_data(bar)

        # subscribe to real-time bar stream
        self.data_provider.subscribe_bars(_handle_bar, self.params.symbol, self.params.timeframe)

        # start streaming; run blocks until interrupted
        try:
            self.data_provider.run()
        except KeyboardInterrupt:
            print("[EMACrossoverStrategy] Stopping live data stream")
        finally:
            # cleanup
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