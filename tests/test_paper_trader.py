import csv
import unittest
from pathlib import Path

from src.paper_trader import Order, PaperTrader


class TestPaperTrader(unittest.TestCase):
    def setUp(self) -> None:
        self.log_path = Path("logs/test_trades.csv")
        if self.log_path.exists():
            self.log_path.unlink()
        self.trader = PaperTrader(1000.0, trades_log_path=self.log_path)

    def tearDown(self) -> None:
        if self.log_path.exists():
            self.log_path.unlink()

    def test_buy_creates_position_and_updates_cash(self) -> None:
        order = Order(symbol="SBER", side="BUY", quantity=5, price=100, stop_loss=95, take_profit=110)
        self.trader.process_order(order)

        self.assertAlmostEqual(self.trader.cash, 500.0)
        position = self.trader.positions["SBER"]
        self.assertEqual(position.quantity, 5)
        self.assertAlmostEqual(position.avg_price, 100.0)
        self.assertEqual(position.stop_loss, 95)
        self.assertEqual(position.take_profit, 110)

        with self.log_path.open() as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "SBER")
        self.assertEqual(rows[0]["side"], "BUY")
        self.assertEqual(rows[0]["stop_loss"], "95")
        self.assertEqual(rows[0]["take_profit"], "110")

    def test_sell_closes_position_and_returns_cash(self) -> None:
        self.trader.process_order(Order(symbol="SBER", side="BUY", quantity=5, price=100))
        self.trader.process_order(Order(symbol="SBER", side="SELL", quantity=5, price=110))

        self.assertAlmostEqual(self.trader.cash, 1000.0 + 50.0)
        self.assertNotIn("SBER", self.trader.positions)

    def test_check_stop_loss_generates_order(self) -> None:
        self.trader.process_order(Order(symbol="SBER", side="BUY", quantity=5, price=100, stop_loss=95))

        stop_order = self.trader.check_stop_take("SBER", current_price=94)
        self.assertIsNotNone(stop_order)
        assert stop_order is not None
        self.assertEqual(stop_order.side, "SELL")
        self.assertEqual(stop_order.quantity, 5)

        self.trader.process_order(stop_order)
        self.assertNotIn("SBER", self.trader.positions)


if __name__ == "__main__":
    unittest.main()
