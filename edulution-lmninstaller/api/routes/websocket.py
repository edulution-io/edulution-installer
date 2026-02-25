from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.services.output_streamer import streamer

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/output")
async def websocket_output(websocket: WebSocket) -> None:
    await streamer.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        streamer.disconnect(websocket)
