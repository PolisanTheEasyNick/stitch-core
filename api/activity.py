from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect, Request, Header, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
import asyncio
from typing import Annotated

from core.config import DIGEST_BEARER
from .base import APIModule
from core.logger import get_logger

activity_data = {
    "phone_battery": None,
    "wearos_battery": None,
    "phone_activity": None,
    "wearos_activity": None
}

connected_clients = set()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

logger = get_logger("Activity")

async def notify_clients(data):
    logger.debug("Notifying WS clients")
    global connected_clients
    alive = set()
    for ws in connected_clients:
        try:
            await ws.send_json(data)
            alive.add(ws)
        except Exception:
            pass
    connected_clients = alive

async def verify_token(token: Annotated[str, Depends(oauth2_scheme)]):
    logger.debug("Veryfing OAuth2 Token")
    if token != DIGEST_BEARER:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return token

class ActivityModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:
        @router.post("/activity")
        async def update_activity(request: Request, token: Annotated[str, Depends(verify_token)]):
            incoming = await request.json()
            logger.debug(f"POST request with {incoming}")
            updated = False
            for key in activity_data:
                if key in incoming:
                    activity_data[key] = incoming[key]
                    updated = True
            if updated:
                await notify_clients(activity_data)
            return {"status": "ok"}

        @router.get("/activity")
        async def get_activity():
            logger.debug("GET request")
            return activity_data

    def register_websockets(self, app: FastAPI):
        @app.websocket("/activity")
        async def activity_ws(websocket: WebSocket):
            logger.debug("WS Connected")
            await websocket.accept()
            connected_clients.add(websocket)
            try:
                await websocket.send_json(activity_data)
                while True:
                    await asyncio.sleep(KEEP_ALIVE)
            except WebSocketDisconnect:
                connected_clients.remove(websocket)
