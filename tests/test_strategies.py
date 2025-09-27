import unittest

import pandas as pd

from src.strategies import (
    breakout_strategy,
    rsi_strategy,
    sma_cross_strategy,
)


class TestStrategies(unittest.TestCase):
    def test_sma_cross_strategy_buy_signal(self) -> None:
        df = pd.DataFrame({
            "close": [10, 10, 10, 10, 9, 12],
        })

        signal = sma_cross_strategy(df, fast_period=2, slow_period=4)

        self.assertEqual(signal, "BUY")

    def test_rsi_strategy_buy_sell_signals(self) -> None:
        descending = pd.DataFrame({"close": [50, 48, 46, 44, 42, 40]})
        ascending = pd.DataFrame({"close": [40, 42, 44, 46, 48, 50]})

        buy_signal = rsi_strategy(descending, period=3, lower_threshold=35, upper_threshold=65)
        sell_signal = rsi_strategy(ascending, period=3, lower_threshold=35, upper_threshold=65)

        self.assertEqual(buy_signal, "BUY")
        self.assertEqual(sell_signal, "SELL")

    def test_breakout_strategy_buy_signal(self) -> None:
        df = pd.DataFrame({
            "high": [10, 11, 12, 13, 14, 15],
            "low": [9, 10, 11, 12, 13, 14],
            "close": [9.5, 10.5, 11.5, 12.5, 13.5, 16],
        })

        signal = breakout_strategy(df, lookback=5)

        self.assertEqual(signal, "BUY")


if __name__ == "__main__":
    unittest.main()
