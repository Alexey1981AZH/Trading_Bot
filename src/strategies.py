"""Индикаторы и торговые стратегии на базе свечных данных pandas."""
from __future__ import annotations

from typing import Literal, Tuple

import numpy as np
import pandas as pd

Signal = Literal["BUY", "SELL", "HOLD"]


def sma(series: pd.Series, period: int) -> pd.Series:
    """Простое скользящее среднее."""
    if period <= 0:
        raise ValueError("Период SMA должен быть положительным.")
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Экспоненциальное скользящее среднее."""
    if period <= 0:
        raise ValueError("Период EMA должен быть положительным.")
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Индекс относительной силы (RSI)."""
    if period <= 0:
        raise ValueError("Период RSI должен быть положительным.")

    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    rsi_series = rsi_series.where(avg_loss != 0, 100)
    rsi_series = rsi_series.where(avg_gain != 0, 0)
    return rsi_series.fillna(0)


def bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Полосы Боллинджера: средняя, верхняя и нижняя границы."""
    if period <= 0:
        raise ValueError("Период Bollinger Bands должен быть положительным.")
    if num_std <= 0:
        raise ValueError("Количество сигм должно быть положительным.")

    middle = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    return middle, upper, lower


def sma_cross_strategy(
    candles: pd.DataFrame,
    *,
    fast_period: int = 9,
    slow_period: int = 21,
    price_column: str = "close",
) -> Signal:
    """Стратегия пересечения быстрых и медленных SMA."""
    if fast_period >= slow_period:
        raise ValueError("Быстрый период должен быть меньше медленного.")
    if price_column not in candles:
        raise ValueError(f"В DataFrame отсутствует столбец '{price_column}'.")

    prices = candles[price_column].astype(float)
    fast_ma = sma(prices, fast_period)
    slow_ma = sma(prices, slow_period)

    if len(candles) < slow_period + 1 or fast_ma.iloc[-2:].isna().any() or slow_ma.iloc[-2:].isna().any():
        return "HOLD"

    prev_fast, curr_fast = fast_ma.iloc[-2], fast_ma.iloc[-1]
    prev_slow, curr_slow = slow_ma.iloc[-2], slow_ma.iloc[-1]

    if curr_fast > curr_slow and prev_fast <= prev_slow:
        return "BUY"
    if curr_fast < curr_slow and prev_fast >= prev_slow:
        return "SELL"
    return "HOLD"


def rsi_strategy(
    candles: pd.DataFrame,
    *,
    period: int = 14,
    lower_threshold: float = 30.0,
    upper_threshold: float = 70.0,
    price_column: str = "close",
) -> Signal:
    """Стратегия по уровням RSI."""
    if price_column not in candles:
        raise ValueError(f"В DataFrame отсутствует столбец '{price_column}'.")

    prices = candles[price_column].astype(float)
    rsi_series = rsi(prices, period)

    if len(rsi_series) == 0 or np.isnan(rsi_series.iloc[-1]):
        return "HOLD"

    latest_rsi = rsi_series.iloc[-1]
    if latest_rsi <= lower_threshold:
        return "BUY"
    if latest_rsi >= upper_threshold:
        return "SELL"
    return "HOLD"


def breakout_strategy(
    candles: pd.DataFrame,
    *,
    lookback: int = 20,
    price_column: str = "close",
) -> Signal:
    """Стратегия пробоя диапазона: выход за пределы максимума/минимума окна."""
    required_columns = {price_column, "high", "low"}
    missing = required_columns - set(candles.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"В DataFrame отсутствуют столбцы: {missing_cols}")

    if len(candles) <= lookback:
        return "HOLD"

    recent = candles.iloc[-1]
    window = candles.iloc[-(lookback + 1):-1]

    highest = window["high"].max()
    lowest = window["low"].min()
    close_price = float(recent[price_column])

    if close_price > highest:
        return "BUY"
    if close_price < lowest:
        return "SELL"
    return "HOLD"


__all__ = [
    "Signal",
    "sma",
    "ema",
    "rsi",
    "bollinger_bands",
    "sma_cross_strategy",
    "rsi_strategy",
    "breakout_strategy",
]
