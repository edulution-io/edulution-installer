import asyncio
from collections import deque
from datetime import datetime
from uuid import UUID

from fastapi import WebSocket

from api.models import MessageType, WebSocketMessage

# Bounds the memory of a run whose output never ends; a normal installation stays far below.
HISTORY_LIMIT = 20000
# A peer that vanished without closing would otherwise hold up the output for everyone.
SEND_TIMEOUT = 10


class OutputStreamer:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._queue: asyncio.Queue[WebSocketMessage] = asyncio.Queue()
        self._current_job_id: UUID | None = None
        # The current run's output, sent first to every connection: a browser that lost the stream
        # or opened the page again sees the whole run, not only what follows.
        self._history: deque[WebSocketMessage] = deque(maxlen=HISTORY_LIMIT)
        # Keeps a broadcast from falling between a connection's replay and its joining the live output.
        self._lock = asyncio.Lock()

    def set_job_id(self, job_id: UUID) -> None:
        self._current_job_id = job_id
        self._history.clear()

    async def connect(self, websocket: WebSocket) -> bool:
        await websocket.accept()
        async with self._lock:
            try:
                for message in list(self._history):
                    await asyncio.wait_for(websocket.send_json(message.model_dump(mode="json")), SEND_TIMEOUT)
            except Exception:
                return False
            self._connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, message: WebSocketMessage) -> None:
        async with self._lock:
            if message.job_id is not None and message.job_id == self._current_job_id:
                self._history.append(message)

            disconnected = []
            for connection in self._connections:
                try:
                    await asyncio.wait_for(connection.send_json(message.model_dump(mode="json")), SEND_TIMEOUT)
                except Exception:
                    disconnected.append(connection)

            for conn in disconnected:
                self.disconnect(conn)

    def queue_message(self, msg_type: MessageType, data: str) -> None:
        message = WebSocketMessage(
            type=msg_type,
            data=data,
            timestamp=datetime.utcnow(),
            job_id=self._current_job_id,
        )
        try:
            self._queue.put_nowait(message)
        except asyncio.QueueFull:
            pass

    async def process_queue(self) -> None:
        while True:
            try:
                message = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                await self.broadcast(message)
            except asyncio.TimeoutError:
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break


streamer = OutputStreamer()
