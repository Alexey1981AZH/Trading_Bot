import unittest

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from src.visualization import TradePoint, plot_equity_curve, plot_price_with_indicators


class TestVisualization(unittest.TestCase):
    def setUp(self) -> None:
        self.dates = pd.date_range("2024-01-01", periods=30, freq="D")
        self.data = pd.DataFrame(
            {
                "close": pd.Series(range(100, 130)),
            },
            index=self.dates,
        )

    def tearDown(self) -> None:
        plt.close("all")

    def test_plot_price_with_indicators_returns_figure(self) -> None:
        trades = [
            TradePoint(timestamp=self.dates[5], price=105, side="BUY"),
            TradePoint(timestamp=self.dates[10], price=110, side="SELL"),
        ]

        fig = plot_price_with_indicators(
            self.data,
            sma_periods=(3, 5),
            bollinger_period=5,
            rsi_period=5,
            trades=trades,
        )

        self.assertIsInstance(fig, matplotlib.figure.Figure)

    def test_plot_equity_curve_returns_figure(self) -> None:
        equity = [1000 + i * 10 for i in range(30)]
        fig = plot_equity_curve(equity)
        self.assertIsInstance(fig, matplotlib.figure.Figure)


if __name__ == "__main__":
    unittest.main()
