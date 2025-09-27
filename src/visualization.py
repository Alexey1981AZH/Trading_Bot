"""Визуализация котировок, индикаторов и результатов тестов."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Optional, Sequence

import matplotlib.pyplot as plt
import pandas as pd

from .strategies import bollinger_bands, rsi, sma

TradeSide = Literal["BUY", "SELL"]


@dataclass
class TradePoint:
    """Точка входа/выхода для отображения на графике."""

    timestamp: pd.Timestamp
    price: float
    side: TradeSide


def plot_price_with_indicators(
    candles: pd.DataFrame,
    *,
    price_column: str = "close",
    sma_periods: Sequence[int] = (9, 21),
    bollinger_period: int = 20,
    bollinger_std: float = 2.0,
    rsi_period: int = 14,
    trades: Optional[Iterable[TradePoint]] = None,
) -> plt.Figure:
    """Создаёт график цены с индикаторами и точками сделок."""

    if price_column not in candles:
        raise ValueError(f"В DataFrame должен быть столбец '{price_column}'.")

    df = candles.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        if "timestamp" in df:
            df.index = pd.to_datetime(df["timestamp"])
        else:
            raise ValueError("Для построения графика требуется DatetimeIndex или столбец 'timestamp'.")

    close = df[price_column].astype(float)

    sma_values = {period: sma(close, period) for period in sma_periods}
    middle, upper, lower = bollinger_bands(close, period=bollinger_period, num_std=bollinger_std)
    rsi_series = rsi(close, period=rsi_period)

    fig, (ax_price, ax_rsi) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})

    # Цена и индикаторы
    ax_price.plot(df.index, close, label="Close", color="#1f77b4")
    for period, series in sma_values.items():
        ax_price.plot(df.index, series, label=f"SMA {period}")

    ax_price.fill_between(df.index, upper, lower, color="#c5d7f2", alpha=0.3, label="Bollinger")

    if trades:
        buys_x, buys_y = [], []
        sells_x, sells_y = [], []
        for trade in trades:
            if isinstance(trade.timestamp, str):
                timestamp = pd.to_datetime(trade.timestamp)
            else:
                timestamp = pd.to_datetime(trade.timestamp)
            if trade.side == "BUY":
                buys_x.append(timestamp)
                buys_y.append(trade.price)
            else:
                sells_x.append(timestamp)
                sells_y.append(trade.price)
        if buys_x:
            ax_price.scatter(buys_x, buys_y, marker="^", color="#2ca02c", label="Buy", zorder=5)
        if sells_x:
            ax_price.scatter(sells_x, sells_y, marker="v", color="#d62728", label="Sell", zorder=5)

    ax_price.set_ylabel("Цена")
    ax_price.legend(loc="upper left")
    ax_price.grid(True, alpha=0.3)

    # RSI на отдельной оси
    ax_rsi.plot(df.index, rsi_series, label="RSI", color="#ff7f0e")
    ax_rsi.axhline(70, color="#d62728", linestyle="--", linewidth=1)
    ax_rsi.axhline(30, color="#2ca02c", linestyle="--", linewidth=1)
    ax_rsi.set_ylabel("RSI")
    ax_rsi.set_xlabel("Дата")
    ax_rsi.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig


def plot_equity_curve(equity: Sequence[float], *, title: str = "Кривая доходности") -> plt.Figure:
    """Строит график динамики капитала/доходности."""

    if not equity:
        raise ValueError("Для построения кривой доходности требуется непустая последовательность.")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(range(len(equity)), equity, color="#1f77b4")
    ax.set_title(title)
    ax.set_xlabel("Шаг")
    ax.set_ylabel("Баланс")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


__all__ = ["TradePoint", "plot_price_with_indicators", "plot_equity_curve"]
