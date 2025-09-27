import asyncio
import json
import unittest
from typing import List
from unittest.mock import MagicMock, patch

from src.alor_client import AlorAuthError, AlorClient


class TestAlorClientREST(unittest.TestCase):
    def setUp(self) -> None:
        self.session = MagicMock()
        self.client = AlorClient(
            "test-token",
            base_rest_url="https://example.com",
            base_ws_url="wss://example.com",
            session=self.session,
        )

    def test_get_historical_candles_returns_50_items(self) -> None:
        candles = [{"time": i, "open": 1.0, "close": 1.0} for i in range(50)]
        response = MagicMock()
        response.status_code = 200
        response.ok = True
        response.json.return_value = {"candles": candles}
        self.session.get.return_value = response

        result = list(self.client.get_historical_candles("SBER", limit=50))

        self.assertEqual(len(result), 50)
        self.session.get.assert_called_once()
        url = "https://example.com/md/v2/history/MOEX/SBER"
        self.session.get.assert_called_with(
            url,
            headers={"Authorization": "Bearer test-token", "Accept": "application/json"},
            params={"limit": 50, "timeframe": "1"},
            timeout=10,
        )

    def test_get_historical_candles_raises_on_invalid_token(self) -> None:
        response = MagicMock()
        response.status_code = 401
        response.ok = False
        response.text = "Unauthorized"
        self.session.get.return_value = response

        with self.assertRaises(AlorAuthError):
            list(self.client.get_historical_candles("SBER"))


class DummyWebSocket:
    def __init__(self, messages: List[str]):
        self.messages = messages
        self.sent_frames: List[str] = []

    async def __aenter__(self) -> "DummyWebSocket":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def send(self, message: str) -> None:
        self.sent_frames.append(message)

    async def recv(self) -> str:
        if self.messages:
            return self.messages.pop(0)
        await asyncio.sleep(0)
        return json.dumps({})


class TestAlorClientWebSocket(unittest.IsolatedAsyncioTestCase):
    async def test_subscribe_quotes_passes_payload_to_callback(self) -> None:
        client = AlorClient(
            "test-token",
            base_rest_url="https://example.com",
            base_ws_url="wss://example.com",
        )

        message = json.dumps({"symbol": "USD/RUB", "price": 95.1})
        dummy_ws = DummyWebSocket([message])

        callback_results = []

        def callback(payload):
            callback_results.append(payload)

        with patch.object(client, "_connect_ws", return_value=dummy_ws):
            await client.subscribe_quotes(
                "USD/RUB",
                exchange="CETS",
                callback=callback,
                max_messages=1,
            )

        self.assertEqual(len(callback_results), 1)
        self.assertEqual(callback_results[0]["symbol"], "USD/RUB")


if __name__ == "__main__":
    unittest.main()
