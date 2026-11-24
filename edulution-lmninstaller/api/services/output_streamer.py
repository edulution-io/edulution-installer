import asyncio
import contextlib
import itertools
from collections import deque
from datetime import datetime
from uuid import UUID

from fastapi import WebSocket

from api.models import MessageType, WebSocketMessage

# Bounds the memory of a run whose output never ends; a normal installation stays far below.
HISTORY_LIMIT = 20000
# A client that does not take a message in this time is closed, so it reconnects and gets the replay.
SEND_TIMEOUT = 10


class _Client:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        # Its own queue: a slow replay to one client does not hold up the others.
        self.queue: asyncio.Queue[WebSocketMessage] = asyncio.Queue()
        self.task: asyncio.Task | None = None


class OutputStreamer:
    def __init__(self):
        self._clients: dict[WebSocket, _Client] = {}
        self._queue: asyncio.Queue[WebSocketMessage] = asyncio.Queue()
        self._current_job_id: UUID | None = None
        # The current run's output, sent first to every connection: a browser that lost the stream
        # or opened the page again sees the whole run, not only what follows.
        self._history: deque[WebSocketMessage] = deque(maxlen=HISTORY_LIMIT)
        # Messages the current run has had, also those the limit dropped: positions for output_since.
        self._history_total = 0

    def set_job_id(self, job_id: UUID) -> None:
        self._current_job_id = job_id
        self._history.clear()
        self._history_total = 0

    @property
    def job_id(self) -> UUID | None:
        return self._current_job_id

    def output_since(self, position: int, limit: int) -> tuple[int, list[WebSocketMessage], int]:
        """The current run's messages from position on, for a client without the stream: (first, messages, total)."""
        first = max(position, self._history_total - len(self._history))
        skip = first - (self._history_total - len(self._history))
        return first, list(itertools.islice(self._history, skip, skip + limit)), self._history_total

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        client = _Client(websocket)
        # No await between copying the history and registering, so no message falls in between.
        for message in self._history:
            client.queue.put_nowait(message)
        self._clients[websocket] = client
        client.task = asyncio.create_task(self._send(client))

    def disconnect(self, websocket: WebSocket) -> None:
        client = self._clients.pop(websocket, None)
        if client and client.task:
            client.task.cancel()

    async def _send(self, client: _Client) -> None:
        try:
            while True:
                message = await client.queue.get()
                await asyncio.wait_for(client.websocket.send_json(message.model_dump(mode="json")), SEND_TIMEOUT)
        except asyncio.CancelledError:
            raise
        except Exception:
            self._clients.pop(client.websocket, None)
            with contextlib.suppress(Exception):
                await asyncio.wait_for(client.websocket.close(), SEND_TIMEOUT)

    async def broadcast(self, message: WebSocketMessage) -> None:
        if message.job_id is not None and message.job_id == self._current_job_id:
            self._history.append(message)
            self._history_total += 1
        for client in self._clients.values():
            client.queue.put_nowait(message)

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
