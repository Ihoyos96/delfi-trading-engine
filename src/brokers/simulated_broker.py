from typing import Type, Dict, Any
from types import SimpleNamespace

class SimulatedBroker:
    """Simple broker simulator with slippage, commission, and position tracking."""

    def __init__(
        self,
        start_cash: float = 100000.0,
        slippage: float = 0.0001,
        commission: float = 0.0002
    ) -> None:
        self.start_cash = start_cash
        self.cash = start_cash
        self.slippage = slippage
        self.commission = commission
        self.trades = []  # list of trade records
        self.positions = []  # open positions

    async def place_order(
        self,
        side: str,
        size: float,
        price: float,
        symbol: str,
        order_type: str = "limit"
    ) -> None:
        """Execute order immediately with slippage & commission. 'symbol' and 'order_type' parameters are accepted but ignored."""
        # adjust for slippage
        fill_price = price * (1 + self.slippage) if side.upper() == 'BUY' else price * (1 - self.slippage)
        cost = fill_price * size
        fee = abs(cost) * self.commission

        # update cash and positions
        if side.upper() == 'BUY':
            self.cash -= cost + fee
            self.positions.append({'symbol': symbol, 'side': 'LONG', 'size': size, 'entry': fill_price, 'commission': fee})
        else:
            # SELL means short
            self.cash += cost - fee
            self.positions.append({'symbol': symbol, 'side': 'SHORT', 'size': size, 'entry': fill_price, 'commission': fee})

        # record trade
        self.trades.append({'side': side.upper(), 'size': size, 'price': fill_price, 'commission': fee})

    def close_positions(self, last_price: float) -> None:
        """Mark-to-market and close all open positions at last_price."""
        for pos in self.positions:
            if pos['side'] == 'LONG':
                pnl = (last_price - pos['entry']) * pos['size'] - pos['commission']
            else:
                pnl = (pos['entry'] - last_price) * pos['size'] - pos['commission']
            self.cash += pnl
        self.positions = []

    def performance(self) -> Dict[str, Any]:
        """Return basic performance metrics."""
        return {
            'start_cash': self.start_cash,
            'final_cash': self.cash,
            'total_return': (self.cash / self.start_cash - 1),
            'trades': len(self.trades)
        }

    async def get_account(self):
        """Return simulated account with cash and equity attributes."""
        # Simulated equity equals current cash (ignoring open positions for simplicity)
        return SimpleNamespace(cash=self.cash, equity=self.cash)

    async def get_all_positions(self):
        """Return a list of current open positions."""
        return self.positions

    async def get_orders(self, status: str = "open", side: str = "sell"):
        """Return empty list (no order book in simulation)."""
        return []