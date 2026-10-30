import asyncio
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import HTTPConnection
from starlette.websockets import WebSocketClose

from api.config import settings
from api.models import JobStatus
from api.routes import playbook, websocket
from api.services.ansible_runner import runner_service
from api.services.lifecycle import remove_install_leftovers, stop_when_idle, touch
from api.services.output_streamer import streamer


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [
        asyncio.create_task(streamer.process_queue()),
        asyncio.create_task(stop_when_idle(runner_service)),
    ]

    yield

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    if runner_service.status != JobStatus.RUNNING:
        remove_install_leftovers()


# Read at import, so uvicorn exits right away instead of starting without a usable token.
API_TOKEN = settings.api_token_file.read_text().strip()
if not API_TOKEN:
    raise RuntimeError(f"{settings.api_token_file} is empty")


class RequireApiToken:
    """Every HTTP and WebSocket request must carry the token bootstrap.sh stored, as a Bearer header."""

    def __init__(self, app):
        self.app = app
        self.expected = f"Bearer {API_TOKEN}".encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)

        given = HTTPConnection(scope).headers.get("authorization", "").encode()
        if secrets.compare_digest(given, self.expected):
            touch()
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
