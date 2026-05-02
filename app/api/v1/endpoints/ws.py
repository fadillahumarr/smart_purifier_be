from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.redis import redis_client

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/monitoring/{purifier_id}")
async def monitoring_ws(websocket: WebSocket, purifier_id: str):
    await websocket.accept()

    pubsub = redis_client.pubsub()
    channel = f"sensor:realtime:{purifier_id}"

    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            await websocket.send_text(message["data"])

    except WebSocketDisconnect:
        pass

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
