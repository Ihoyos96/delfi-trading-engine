import asyncio
import os
import json
from datetime import datetime
from typing import Type, Dict, Any
from inspect import signature

from src.data_providers.base_data_provider import BaseDataProvider
from src.strategies.base_strategy import BaseStrategy
from src.brokers.simulated_broker import SimulatedBroker

class Backtester:
    """Run a BaseStrategy over historical bar data and simulate trades."""

    def __init__(
        self,
        strategy_cls: Type[BaseStrategy],
        config: Dict[str, Any],
        data_provider: BaseDataProvider,
        start_cash: float = 100000.0,
        slippage: float = 0.0001,
        commission: float = 0.0002
    ) -> None:
        self.strategy_cls = strategy_cls
        self.config = config
        self.data_provider = data_provider
        self.start_cash = start_cash
        self.slippage = slippage
        self.commission = commission

    def run(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = '1Min'
    ) -> Dict[str, Any]:
        # fetch data via provider
        df = self.data_provider.get_historical_bars(symbol, start, end, timeframe)
        if df.empty:
            raise ValueError('No data fetched for symbol')

        # init simulation
        broker = SimulatedBroker(self.start_cash, self.slippage, self.commission)
        # Dynamically instantiate strategy: always pass params first, include broker if constructor accepts it
        sig = signature(self.strategy_cls.__init__)
        param_names = list(sig.parameters.keys())[1:]  # skip 'self'
        if param_names and param_names[0] in ('params', 'config'):
            # build positional args
            args = [self.config]
            if 'broker' in param_names:
                args.append(broker)
            strategy = self.strategy_cls(*args)
        elif param_names[:2] in (['broker', 'config'], ['broker', 'params']):
            # backwards compatibility: __init__(self, broker, config)
            strategy = self.strategy_cls(broker, self.config)
        else:
            raise TypeError(f"Unsupported constructor signature for {self.strategy_cls}: {param_names}")

        # run strategy hooks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(strategy.on_start())

        # feed bars
        for _, bar in df.iterrows():
            tick = {
                'open': float(bar['open']),
                'high': float(bar['high']),
                'low': float(bar['low']),
                'close': float(bar['close']),
                'volume': float(bar['volume'])
            }
            loop.run_until_complete(strategy.process_new_bar(tick))

        loop.run_until_complete(strategy.on_stop())
        loop.close()

        # close any open positions
        last_price = float(df.iloc[-1]['close'])
        broker.close_positions(last_price)

        # save trades to file
        os.makedirs('backtests', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        filename = f"backtests/backtest-{self.strategy_cls.__name__}-{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(broker.trades, f, indent=2)
        print(f"Saved trades to {filename}")
        # return performance report
        return broker.performance() 