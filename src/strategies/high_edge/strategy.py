from collections import deque
from typing import Any, Dict
import statistics

from src.strategies.high_edge.params import HighEdgeParams
from src.strategies.base_strategy import BaseStrategy
from src.backtester.backtester import Backtester

class HighEdgeStrategy(BaseStrategy):
    """High Edge Strategy Phase 1 with momentum deadband, z-score reversal, ATR stops, and cooldown."""
    def __init__(self, params: HighEdgeParams, broker: Any = None, data_provider: Any = None) -> None:
        super().__init__(params, broker, data_provider)
        # Parameters
        self.short_window = params.short_window
        self.long_window = params.long_window
        self.ema_threshold = params.ema_threshold
        self.zscore_window = params.zscore_window
        self.zscore_threshold = params.zscore_threshold
        self.atr_window = params.atr_window
        self.stop_atr_mult = params.stop_atr_mult
        self.target_mult = params.target_mult
        self.size = params.size
        self.cooldown = params.cooldown
        # Internal state
        max_len = max(self.long_window, self.zscore_window, self.atr_window)
        self.prices = deque(maxlen=max_len)
        self.volumes = deque(maxlen=self.zscore_window)
        self.price_volume = deque(maxlen=self.zscore_window)
        self.trs = deque(maxlen=self.atr_window)
        self.short_ema = None
        self.long_ema = None
        self.position = 0
        self.entry_price = None
        self.stop_price = None
        self.target_price = None
        self.bars_since_last = self.cooldown
        self.prev_signal = 0
        # Starting equity for drawdown control
        self.start_equity = None

    async def on_start(self) -> None:
        # Reset all buffers and state
        self.prices.clear()
        self.volumes.clear()
        self.price_volume.clear()
        self.trs.clear()
        self.short_ema = None
        self.long_ema = None
        self.position = 0
        self.entry_price = None
        self.stop_price = None
        self.target_price = None
        self.bars_since_last = self.cooldown
        self.prev_signal = 0
        # Record starting equity
        acct = await self.broker.get_account()
        self.start_equity = float(getattr(acct, 'equity', acct.cash))

    async def on_new_data(self, bar: Dict[str, Any]) -> None:
        price = bar.get("close")
        high = bar.get("high")
        low = bar.get("low")
        volume = bar.get("volume", 0)
        if price is None or high is None or low is None:
            return

        # Cooldown tracking and ATR update
        self.bars_since_last += 1
        self.trs.append(high - low)

        # Exit logic: stop-loss or take-profit
        if self.position != 0:
            if self.position == 1:
                if low <= self.stop_price or high >= self.target_price:
                    await self.broker.place_order(
                        side="SELL", size=self.size,
                        price=price, symbol=self.params.symbol,
                        order_type="market"
                    )
                    self.position = 0
                    self.prev_signal = 0
                    self.bars_since_last = 0
                    return
            else:
                if high >= self.stop_price or low <= self.target_price:
                    await self.broker.place_order(
                        side="BUY", size=self.size,
                        price=price, symbol=self.params.symbol,
                        order_type="market"
                    )
                    self.position = 0
                    self.prev_signal = 0
                    self.bars_since_last = 0
                    return

        # Rolling data updates
        self.prices.append(price)
        self.volumes.append(volume)
        self.price_volume.append(price * volume)

        # Need sufficient history
        if len(self.prices) < self.long_window or len(self.price_volume) < self.zscore_window:
            return

        # EMA updates
        alpha_s = 2 / (self.short_window + 1)
        alpha_l = 2 / (self.long_window + 1)
        if self.short_ema is None:
            self.short_ema = price
            self.long_ema = price
        else:
            self.short_ema = alpha_s * price + (1 - alpha_s) * self.short_ema
            self.long_ema = alpha_l * price + (1 - alpha_l) * self.long_ema

        # Momentum deadband filter
        diff = self.short_ema - self.long_ema
        if diff > self.ema_threshold * price:
            momentum = 1
        elif diff < -self.ema_threshold * price:
            momentum = -1
        else:
            momentum = 0

        # VWAP z-score
        total_vol = sum(self.volumes)
        vwap = sum(self.price_volume) / total_vol if total_vol else price
        recent = list(self.prices)[-self.zscore_window:]
        stdev = statistics.pstdev(recent) if len(recent) > 1 else 0.0
        zscore = (price - vwap) / stdev if stdev > 0 else 0.0
        if zscore < -self.zscore_threshold:
            reversion = 1
        elif zscore > self.zscore_threshold:
            reversion = -1
        else:
            reversion = 0

        # Final signal: prefer reversion over momentum
        signal = reversion if reversion != 0 else momentum

        # Entry logic: only on crossing, cooldown, flat, and risk checks
        if signal != 0 and signal != self.prev_signal and self.bars_since_last >= self.cooldown and self.position == 0:
            # Risk control: daily drawdown cap
            acct_cur = await self.broker.get_account()
            equity_cur = float(getattr(acct_cur, 'equity', acct_cur.cash))
            drawdown = (self.start_equity - equity_cur) / self.start_equity
            if drawdown >= self.params.daily_drawdown:
                return
            # Risk control: concurrent position limits
            pos_list = await self.broker.get_all_positions()
            # total open positions
            if len(pos_list) >= self.params.max_total_positions:
                return
            # per-symbol open positions
            same_sym = sum(1 for p in pos_list if p.get('symbol') == self.params.symbol)
            if same_sym >= self.params.max_positions_per_symbol:
                return
            # Risk control: no duplicate open orders for this symbol
            open_orders = []
            for side_check in ("buy", "sell"):
                try:
                    open_orders.extend(await self.broker.get_orders(status="open", side=side_check))
                except Exception:
                    pass
            for o in open_orders:
                # Alpaca orders and simulated orders may differ in attribute names
                if getattr(o, 'symbol', getattr(o, 'symbol', None)) == self.params.symbol:
                    return
            # Compute ATR-based stop and target
            atr = sum(self.trs) / len(self.trs) if self.trs else 0.0
            stop_dist = self.stop_atr_mult * atr
            target_dist = self.target_mult * stop_dist
            self.entry_price = price
            if signal == 1:
                self.stop_price = price - stop_dist
                self.target_price = price + target_dist
                side = "BUY"
            else:
                self.stop_price = price + stop_dist
                self.target_price = price - target_dist
                side = "SELL"

            # Dynamic sizing: use `size` param as fraction of equity
            acct = await self.broker.get_account()
            equity = float(getattr(acct, 'equity', acct.cash))
            order_size = (equity * self.size) / price
            await self.broker.place_order(
                side=side,
                size=order_size,
                price=price,
                symbol=self.params.symbol,
                order_type="market"
            )
            self.position = signal
            self.prev_signal = signal
            self.bars_since_last = 0

    async def on_stop(self) -> None:
        # No special cleanup
        pass

    def run(self) -> None:
        import asyncio
        asyncio.run(self.on_start())

        async def handler(bar):
            await self.on_new_data(bar)

        self.data_provider.subscribe_bars(handler, self.params.symbol, self.params.timeframe)
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