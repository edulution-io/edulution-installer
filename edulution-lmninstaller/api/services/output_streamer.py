import asyncio
from datetime import datetime
from uuid import UUID

from fastapi import WebSocket

from api.models import MessageType, WebSocketMessage


class OutputStreamer:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._queue: asyncio.Queue[WebSocketMessage] = asyncio.Queue()
        self._current_job_id: UUID | None = None

    def set_job_id(self, job_id: UUID) -> None:
        self._current_job_id = job_id

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, message: WebSocketMessage) -> None:
        disconnected = []
        for connection in self._connections:
            try:
                await connection.send_json(message.model_dump(mode="json"))
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
