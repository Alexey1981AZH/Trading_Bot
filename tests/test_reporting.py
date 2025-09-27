import csv
import unittest
from pathlib import Path

from src.paper_trader import Order, PaperTrader
from src.reporting import TradingReport, generate_report


class TestReporting(unittest.TestCase):
    def setUp(self) -> None:
        self.log_path = Path("logs/test_report.csv")
        if self.log_path.exists():
            self.log_path.unlink()
        self.initial_cash = 1000.0

    def tearDown(self) -> None:
        if self.log_path.exists():
            self.log_path.unlink()

    def test_report_without_trades(self) -> None:
        report = generate_report(self.initial_cash, trades_log_path=self.log_path)

        self.assertIsInstance(report, TradingReport)
        self.assertEqual(report.final_balance, self.initial_cash)
        self.assertEqual(report.pnl, 0.0)
        self.assertEqual(report.return_pct, 0.0)
        self.assertEqual(report.max_drawdown_pct, 0.0)

    def test_report_with_trades(self) -> None:
        trader = PaperTrader(self.initial_cash, trades_log_path=self.log_path)
        trader.process_order(Order(symbol="SBER", side="BUY", quantity=5, price=100))
        trader.process_order(Order(symbol="SBER", side="SELL", quantity=5, price=80))

        report = generate_report(self.initial_cash, trades_log_path=self.log_path)

        self.assertAlmostEqual(report.final_balance, 900.0)
        self.assertAlmostEqual(report.pnl, -100.0)
        self.assertAlmostEqual(report.return_pct, -10.0)
        self.assertAlmostEqual(report.max_drawdown_pct, 50.0)


if __name__ == "__main__":
    unittest.main()
