"""In-memory history and WebSocket delivery for externally submitted images."""
import asyncio
import logging
import threading
from collections import deque
from typing import Deque, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from backend.app.schemas.incident import UploadAnalysisResponse

logger = logging.getLogger(__name__)


class ImageIngestionService:
    def __init__(self, history_limit: int = 20) -> None:
        self._history: Deque[UploadAnalysisResponse] = deque(maxlen=history_limit)
        self._history_lock = threading.Lock()
        self._clients: Set[WebSocket] = set()
        self._clients_lock = asyncio.Lock()

    def record(self, analysis: UploadAnalysisResponse) -> UploadAnalysisResponse:
        with self._history_lock:
            self._history.append(analysis)
        return analysis

    def recent(self, limit: int = 20) -> list[UploadAnalysisResponse]:
        with self._history_lock:
            batches = list(self._history)[-limit:]
        return [batch.model_copy(deep=True) for batch in reversed(batches)]

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._clients_lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._clients_lock:
            self._clients.discard(websocket)

    async def publish(self, batch: UploadAnalysisResponse) -> None:
        async with self._clients_lock:
            clients = list(self._clients)

        disconnected = []
        payload = {"type": "image_analysis", "batch": batch.model_dump(mode="json")}
        for client in clients:
            try:
                await client.send_json(payload)
            except (RuntimeError, OSError, WebSocketDisconnect) as exc:
                logger.warning("Removing disconnected image-analysis WebSocket client: %s", exc)
                disconnected.append(client)

        if disconnected:
            async with self._clients_lock:
                self._clients.difference_update(disconnected)


image_ingestion_service = ImageIngestionService()
