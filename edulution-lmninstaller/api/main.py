import asyncio
import signal
from contextlib import asynccontextmanager

from fastapi import FastAPI

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


app = FastAPI(
    title="Edulution LMN Installer API",
    description="Mini-API for Ansible playbook execution with real-time output streaming",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(playbook.router)
app.include_router(websocket.router)
