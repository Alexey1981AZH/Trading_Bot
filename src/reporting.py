"""Генерация отчёта по результатам бумажного трейдинга."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass
class TradingReport:
    """Итоговые метрики по счёту."""

    final_balance: float
    pnl: float
    return_pct: float
    max_drawdown_pct: float


def _read_cash_series(trades_log_path: Path, initial_cash: float) -> List[float]:
    if not trades_log_path.exists():
        return [initial_cash]

    cash_values: List[float] = [initial_cash]
    with trades_log_path.open("r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                cash = float(row["cash"])
            except (KeyError, TypeError, ValueError):
                continue
            cash_values.append(cash)

    if not cash_values:
        cash_values.append(initial_cash)
    return cash_values


def _calculate_max_drawdown(values: Iterable[float]) -> float:
    peak = None
    max_drawdown = 0.0

    for value in values:
        if peak is None:
            peak = value
            continue

        if value > peak:
            peak = value

        if peak > 0:
            drawdown = (peak - value) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

    return max_drawdown


def generate_report(initial_cash: float, trades_log_path: Path = Path("logs/trades.csv")) -> TradingReport:
    if initial_cash <= 0:
        raise ValueError("Начальный капитал должен быть положительным.")

    cash_series = _read_cash_series(trades_log_path, initial_cash)
    final_balance = cash_series[-1]
    pnl = final_balance - initial_cash
    return_pct = pnl / initial_cash * 100
    max_drawdown = _calculate_max_drawdown(cash_series)

    return TradingReport(
        final_balance=final_balance,
        pnl=pnl,
        return_pct=return_pct,
        max_drawdown_pct=max_drawdown,
    )


__all__ = ["TradingReport", "generate_report"]
