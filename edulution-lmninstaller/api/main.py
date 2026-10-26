import asyncio
import secrets
import signal
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import HTTPConnection
from starlette.websockets import WebSocketClose

from api.config import settings
from api.routes import playbook, websocket
from api.services.ansible_runner import runner_service
from api.services.output_streamer import streamer


shutdown_event = asyncio.Event()


def trigger_shutdown() -> None:
    async def delayed_shutdown():
        await asyncio.sleep(settings.shutdown_delay)
        shutdown_event.set()

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(delayed_shutdown())
    except RuntimeError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    runner_service.set_shutdown_callback(trigger_shutdown)

    queue_task = asyncio.create_task(streamer.process_queue())

    async def watch_shutdown():
        await shutdown_event.wait()
        import os
        os.kill(os.getpid(), signal.SIGTERM)

    shutdown_task = asyncio.create_task(watch_shutdown())

    yield

    queue_task.cancel()
    shutdown_task.cancel()
    try:
        await queue_task
    except asyncio.CancelledError:
        pass
    try:
        await shutdown_task
    except asyncio.CancelledError:
        pass


class RequireApiToken:
    """Every HTTP and WebSocket request carries the token bootstrap.sh stored, as a Bearer header."""

    def __init__(self, app):
        self.app = app
        self.expected = f"Bearer {settings.api_token_file.read_text().strip()}".encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)

        given = HTTPConnection(scope).headers.get("authorization", "").encode()
        if secrets.compare_digest(given, self.expected):
            return await self.app(scope, receive, send)

        if scope["type"] == "websocket":
            response = WebSocketClose(code=1008)
        else:
            response = JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        await response(scope, receive, send)


app = FastAPI(
    title="Edulution LMN Installer API",
    description="Mini-API for Ansible playbook execution with real-time output streaming",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(RequireApiToken)

app.include_router(playbook.router)
app.include_router(websocket.router)
