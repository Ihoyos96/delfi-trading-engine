from typing import Type, Dict, Any

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
        price: float
    ) -> None:
        """Execute order immediately with slippage & commission."""
        # adjust for slippage
        fill_price = price * (1 + self.slippage) if side.upper() == 'BUY' else price * (1 - self.slippage)
        cost = fill_price * size
        fee = abs(cost) * self.commission

        # update cash and positions
        if side.upper() == 'BUY':
            self.cash -= cost + fee
            self.positions.append({'side': 'LONG', 'size': size, 'entry': fill_price, 'commission': fee})
        else:
            # SELL means short
            self.cash += cost - fee
            self.positions.append({'side': 'SHORT', 'size': size, 'entry': fill_price, 'commission': fee})

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