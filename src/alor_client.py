"""Клиент для работы с Alor OpenAPI.

Предоставляет базовые методы REST и WebSocket для получения данных рынка.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional, Union

import requests
import websockets
from requests import Response
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosedError, WebSocketException


class AlorAPIError(Exception):
    """Базовое исключение для ошибок Alor API."""


class AlorAuthError(AlorAPIError):
    """Ошибка авторизации или неверного токена."""


class AlorConnectionError(AlorAPIError):
    """Ошибка сетевого соединения или веб-сокета."""


@dataclass
class CandleRequest:
    """Параметры запроса исторических свечей."""

    symbol: str
    exchange: str = "MOEX"
    interval: str = "1"
    limit: int = 50

    def to_params(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "interval": self.interval,
            "limit": self.limit,
        }


class AlorClient:
    """Клиент Alor OpenAPI для REST и WebSocket операций."""

    def __init__(
        self,
        token: str,
        *,
        base_rest_url: str = "https://api.alor.ru",
        base_ws_url: str = "wss://api.alor.ru/ws",
        rest_timeout: int = 10,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not token:
            raise AlorAuthError("Токен авторизации обязателен.")

        self._token = token
        self.base_rest_url = base_rest_url.rstrip("/")
        self.base_ws_url = base_ws_url.rstrip("/")
        self.rest_timeout = rest_timeout
        self._session = session or requests.Session()

    # -------------------------- REST методы -------------------------
    def get_historical_candles(
        self,
        symbol: str,
        *,
        exchange: str = "MOEX",
        interval: str = "1",
        limit: int = 50,
    ) -> Iterable[Dict[str, Any]]:
        """Возвращает исторические свечи для инструмента.

        Параметры совпадают с документацией Alor: интервал (таймфрейм) задаётся
        строкой. В случае успеха возвращает итерируемую коллекцию словарей.
        """

        request = CandleRequest(symbol=symbol, exchange=exchange, interval=interval, limit=limit)
        endpoint = f"{self.base_rest_url}/md/v2/history/{request.exchange}/{request.symbol}"
        params = {"limit": request.limit, "timeframe": request.interval}

        response = self._safe_get(endpoint, params=params)
        data = self._safe_json(response)
        candles = data.get("candles") if isinstance(data, dict) else data
        if candles is None:
            raise AlorAPIError("Ответ не содержит данных по свечам.")
        return candles

    def get_order_book(
        self,
        symbol: str,
        *,
        exchange: str = "MOEX",
        depth: int = 10,
    ) -> Dict[str, Any]:
        """Возвращает стакан (bid/ask) для инструмента."""

        endpoint = f"{self.base_rest_url}/md/v2/orderBook/{exchange}/{symbol}"
        params = {"depth": depth}
        response = self._safe_get(endpoint, params=params)
        return self._safe_json(response)

    def _safe_get(self, url: str, *, params: Optional[Dict[str, Any]] = None) -> Response:
        headers = self._auth_headers()
        try:
            response = self._session.get(url, headers=headers, params=params, timeout=self.rest_timeout)
        except requests.exceptions.RequestException as exc:
            raise AlorConnectionError(f"Ошибка соединения при обращении к {url}: {exc}") from exc

        if response.status_code == 401:
            raise AlorAuthError("Неверный или просроченный токен авторизации.")

        if not response.ok:
            raise AlorAPIError(
                f"Alor API вернул статус {response.status_code}: {response.text[:200]}"
            )

        return response

    @staticmethod
    def _safe_json(response: Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise AlorAPIError("Некорректный JSON в ответе сервера.") from exc

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    # ----------------------- WebSocket методы ----------------------
    async def subscribe_quotes(
        self,
        symbol: str,
        *,
        exchange: str = "MOEX",
        callback: Union[Callable[[Dict[str, Any]], Any], Callable[[Dict[str, Any]], Awaitable[Any]]],
        reconnect_attempts: int = 3,
        reconnect_delay: float = 1.0,
        max_messages: Optional[int] = None,
    ) -> None:
        """Подписывается на котировки инструмента и вызывает callback для каждого сообщения.

        Параметр ``max_messages`` позволяет ограничить количество полученных сообщений (удобно для тестов).
        """

        attempts = 0
        subscriptions_sent = False

        while attempts <= reconnect_attempts:
            try:
                async with self._connect_ws() as websocket:
                    await self._send_subscription(websocket, symbol, exchange)
                    subscriptions_sent = True

                    received = 0
                    while True:
                        raw_message = await websocket.recv()
                        payload = self._parse_ws_message(raw_message)
                        await self._dispatch_callback(callback, payload)
                        received += 1
                        if max_messages is not None and received >= max_messages:
                            return
            except (ConnectionClosedError, WebSocketException) as exc:
                attempts += 1
                if attempts > reconnect_attempts:
                    raise AlorConnectionError("Соединение по WebSocket было прервано и не восстановлено.") from exc
                await asyncio.sleep(reconnect_delay)
            except AlorAuthError:
                # Нет смысла повторять, токен неверный
                raise
            except Exception as exc:  # pylint: disable=broad-except
                raise AlorAPIError(f"Необработанная ошибка при подписке на котировки: {exc}") from exc
            else:
                if subscriptions_sent:
                    return

    async def _dispatch_callback(
        self,
        callback: Union[Callable[[Dict[str, Any]], Any], Callable[[Dict[str, Any]], Awaitable[Any]]],
        payload: Dict[str, Any],
    ) -> None:
        if asyncio.iscoroutinefunction(callback):
            await callback(payload)
        else:
            callback(payload)

    async def _send_subscription(
        self,
        websocket: WebSocketClientProtocol,
        symbol: str,
        exchange: str,
    ) -> None:
        subscribe_message = {
            "opcode": "QuotesSubscribe",
            "code": symbol,
            "exchange": exchange,
            "format": "Simple",
        }
        await websocket.send(json.dumps(subscribe_message))

    def _connect_ws(self) -> Any:
        headers = self._auth_headers()
        return websockets.connect(
            self.base_ws_url,
            extra_headers=headers,
            ping_interval=20,
            ping_timeout=20,
        )

    def _parse_ws_message(self, raw_message: Union[str, bytes]) -> Dict[str, Any]:
        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8")

        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError as exc:
            raise AlorAPIError("Получено сообщение с некорректным JSON из WebSocket.") from exc

        if isinstance(payload, dict) and payload.get("status") == 401:
            raise AlorAuthError("WebSocket сообщил об ошибке авторизации.")

        if not isinstance(payload, dict):
            raise AlorAPIError("Ожидался JSON-объект в сообщении WebSocket.")

        return payload


__all__ = [
    "AlorClient",
    "AlorAPIError",
    "AlorAuthError",
    "AlorConnectionError",
]
