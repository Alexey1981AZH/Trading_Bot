"""Модуль бумажного трейдинга для симуляции сделок без реального рынка."""
from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

TradeSide = str  # "BUY" или "SELL"


@dataclass
class Position:
    """Состояние позиции по конкретному инструменту."""

    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    def update(self, side: TradeSide, quantity: float, price: float) -> None:
        if side == "BUY":
            total_cost = self.avg_price * self.quantity + price * quantity
            self.quantity += quantity
            if self.quantity > 0:
                self.avg_price = total_cost / self.quantity
        elif side == "SELL":
            self.quantity -= quantity
            if self.quantity <= 0:
                self.quantity = 0
                self.avg_price = 0
                self.stop_loss = None
                self.take_profit = None
        else:
            raise ValueError("Неизвестная сторона сделки.")


@dataclass
class Order:
    symbol: str
    side: TradeSide
    quantity: float
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))


class PaperTrader:
    """Симулятор сделок с учётом капитала и позиций."""

    def __init__(
        self,
        initial_cash: float,
        *,
        trades_log_path: Path = Path("logs/trades.csv"),
    ) -> None:
        if initial_cash <= 0:
            raise ValueError("Начальный капитал должен быть положительным.")

        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self._trades_log_path = trades_log_path
        self._ensure_log_header()

    def _ensure_log_header(self) -> None:
        if not self._trades_log_path.parent.exists():
            self._trades_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._trades_log_path.exists():
            with self._trades_log_path.open("w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    ["timestamp", "symbol", "side", "quantity", "price", "stop_loss", "take_profit", "cash"]
                )

    def process_order(self, order: Order) -> None:
        if order.quantity <= 0:
            raise ValueError("Количество должно быть положительным.")
        if order.price <= 0:
            raise ValueError("Цена должна быть положительной.")

        position = self.positions.setdefault(order.symbol, Position(symbol=order.symbol))

        if order.side == "BUY":
            cost = order.quantity * order.price
            if cost > self.cash:
                raise ValueError("Недостаточно средств для покупки.")
            self.cash -= cost
            position.update("BUY", order.quantity, order.price)
        elif order.side == "SELL":
            if position.quantity < order.quantity:
                raise ValueError("Недостаточно лотов для продажи.")
            self.cash += order.quantity * order.price
            position.update("SELL", order.quantity, order.price)
        else:
            raise ValueError("Неизвестная сторона сделки.")

        if order.stop_loss is not None and order.take_profit is not None:
            if order.stop_loss >= order.take_profit:
                raise ValueError("Стоп-лосс должен быть ниже тейк-профита.")

        if position.quantity > 0:
            if order.stop_loss is not None:
                position.stop_loss = order.stop_loss
            if order.take_profit is not None:
                position.take_profit = order.take_profit
        else:
            position.stop_loss = None
            position.take_profit = None

        self._log_trade(order, position)

        if position.quantity == 0:
            self.positions.pop(order.symbol, None)

    def _log_trade(self, order: Order, position: Position) -> None:
        with self._trades_log_path.open("a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    order.timestamp.isoformat(),
                    order.symbol,
                    order.side,
                    order.quantity,
                    order.price,
                    position.stop_loss if position.stop_loss is not None else "",
                    position.take_profit if position.take_profit is not None else "",
                    self.cash,
                ]
            )

    def check_stop_take(self, symbol: str, current_price: float) -> Optional[Order]:
        position = self.positions.get(symbol)
        if not position or position.quantity == 0:
            return None

        if position.stop_loss is not None and current_price <= position.stop_loss:
            return Order(
                symbol=symbol,
                side="SELL",
                quantity=position.quantity,
                price=current_price,
                stop_loss=position.stop_loss,
            )

        if position.take_profit is not None and current_price >= position.take_profit:
            return Order(
                symbol=symbol,
                side="SELL",
                quantity=position.quantity,
                price=current_price,
                take_profit=position.take_profit,
            )
        return None


__all__ = ["PaperTrader", "Order", "Position"]
