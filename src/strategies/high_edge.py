from collections import deque
from typing import Any, Dict
import statistics

from pydantic import BaseModel, Field
from src.config.config import Period
from src.strategies.base_strategy import BaseStrategy
from src.backtester.backtester import Backtester

# Parameters for the High Edge strategy: symbol, timeframes, EMA windows, z-score window and threshold, and order size.
class HighEdgeParams(BaseModel):
    """Runtime parameters for High Edge strategy"""
    symbol: str
    timeframe: str = Field("1Min")
    period: Period
    short_window: int = Field(5, ge=1)
    long_window: int = Field(60, ge=1)
    zscore_window: int = Field(60, ge=1)
    zscore_threshold: float = Field(1.0, gt=0)
    size: float = Field(1.0, gt=0)

# Strategy implementing Phase 1: momentum (EMA crossover) + mean-reversion (VWAP z-score)
class HighEdgeStrategy(BaseStrategy):
    """High Edge Strategy Phase 1: EMA crossover momentum + VWAP z-score mean-reversion"""
    def __init__(self, params: HighEdgeParams, broker: Any = None, data_provider: Any = None) -> None:
        super().__init__(params, broker, data_provider)
        self.short_window = params.short_window
        self.long_window = params.long_window
        self.zscore_window = params.zscore_window
        self.zscore_threshold = params.zscore_threshold
        self.size = params.size
        max_len = max(self.short_window, self.long_window, self.zscore_window)
        self.prices = deque(maxlen=max_len)
        self.volumes = deque(maxlen=self.zscore_window)
        self.price_volume = deque(maxlen=self.zscore_window)
        self.short_ema = None
        self.long_ema = None
        self.position = 0

    async def on_start(self) -> None:
        # Reset buffers and state
        self.prices.clear()
        self.volumes.clear()
        self.price_volume.clear()
        self.short_ema = None
        self.long_ema = None
        self.position = 0

    async def on_new_data(self, bar: Dict[str, Any]) -> None:
        price = bar.get("close")
        volume = bar.get("volume", 0)
        if price is None:
            return

        # Update rolling data
        self.prices.append(price)
        self.volumes.append(volume)
        self.price_volume.append(price * volume)

        # Wait for enough data
        if len(self.prices) < self.long_window or len(self.price_volume) < self.zscore_window:
            return

        # Compute EMAs
        alpha_s = 2 / (self.short_window + 1)
        alpha_l = 2 / (self.long_window + 1)
        if self.short_ema is None:
            self.short_ema = price
            self.long_ema = price
        else:
            self.short_ema = alpha_s * price + (1 - alpha_s) * self.short_ema
            self.long_ema = alpha_l * price + (1 - alpha_l) * self.long_ema

        # Compute VWAP and z-score
        total_vol = sum(self.volumes)
        vwap = sum(self.price_volume) / total_vol if total_vol else price
        recent_prices = list(self.prices)[-self.zscore_window:]
        stdev = statistics.pstdev(recent_prices) if len(recent_prices) > 1 else 0.0
        zscore = (price - vwap) / stdev if stdev > 0 else 0.0

        # Generate signals
        momentum = 1 if self.short_ema > self.long_ema else -1
        if zscore < -self.zscore_threshold:
            reversion = 1
        elif zscore > self.zscore_threshold:
            reversion = -1
        else:
            reversion = 0

        # Final signal
        if momentum == reversion and momentum != 0:
            signal = momentum
        elif reversion != 0:
            signal = reversion
        else:
            signal = momentum

        # Execute on signal change
        if signal == 1 and self.position <= 0:
            await self.broker.place_order(
                side="BUY", size=self.size,
                price=price, symbol=self.params.symbol,
                order_type="market"
            )
            self.position = 1
        elif signal == -1 and self.position >= 0:
            await self.broker.place_order(
                side="SELL", size=self.size,
                price=price, symbol=self.params.symbol,
                order_type="market"
            )
            self.position = -1

    async def on_stop(self) -> None:
        # Cleanup if needed
        pass

    def run(self) -> None:
        import asyncio
        asyncio.run(self.on_start())

        async def _handler(bar):
            await self.on_new_data(bar)

        self.data_provider.subscribe_bars(_handler, self.params.symbol, self.params.timeframe)
        try:
            self.data_provider.run()
        except KeyboardInterrupt:
            pass
        finally:
            asyncio.run(self.on_stop())

    def backtest(self) -> Dict[str, Any]:
        if not self.data_provider:
            raise ValueError("Data provider not set")
        bt = Backtester(self.__class__, self.params, self.data_provider)
        return bt.run(
            self.params.symbol,
            self.params.period.start,
            self.params.period.end,
            self.params.timeframe
        ) 