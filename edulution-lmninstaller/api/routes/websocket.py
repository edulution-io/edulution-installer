from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from api.services.output_streamer import streamer

router = APIRouter(tags=["websocket"])

# Small enough that a page passes the web installer's proxy quickly on a slow link.
OUTPUT_PAGE = 500


@router.get("/api/output")
async def output(since: int = Query(0, ge=0)) -> dict:
    """The run's output over HTTP, for a browser whose WebSocket does not get through (proxy, browser)."""
    first, messages, total = streamer.output_since(since, OUTPUT_PAGE)
    return {
        "job_id": str(streamer.job_id) if streamer.job_id else None,
        "first": first,
        "next": first + len(messages),
        "total": total,
        "messages": [m.model_dump(mode="json") for m in messages],
    }


@router.websocket("/ws/output")
async def websocket_output(websocket: WebSocket) -> None:
    await streamer.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        streamer.disconnect(websocket)
