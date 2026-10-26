from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from api.services.lifecycle import touch
from api.services.output_streamer import streamer

router = APIRouter(tags=["websocket"], dependencies=[Depends(touch)])


@router.websocket("/ws/output")
async def websocket_output(websocket: WebSocket) -> None:
    await streamer.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        streamer.disconnect(websocket)
