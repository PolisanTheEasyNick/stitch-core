from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect, Request, Header, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
import asyncio
from typing import Annotated
import time

from core.config import DIGEST_BEARER
from .base import APIModule
from core.logger import get_logger
from core.main_processor import main_processor
from .configurator import validate

PC_TIMEOUT_SECONDS = 20
pc_last_seen = 0
pc_was_online = False

activity_data = {
    "phone_battery": "OK",
    "wearos_battery": "OK",
    "phone_activity": "CHILL",
    "wearos_activity": "CHILL",
    "pc_status": pc_was_online
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
                await main_processor.handle_activity_update(activity_data)
            return {"status": "ok"}

        @router.get("/activity")
        async def get_activity():
            logger.debug("GET request")
            return activity_data

        @router.post("/ping/pc")
        async def pc_ping(request: Request, token: Annotated[str, Depends(verify_token)]):
            validate(request)
            global pc_last_seen
            pc_last_seen = time.time()
            return {"status": "ok"}

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

    def register_events(self, app: FastAPI):
        @app.on_event("startup")
        async def startup_event():
            async def monitor_pc_status():
                global pc_last_seen, pc_was_online
                while True:
                    await asyncio.sleep(5)
                    now = time.time()
                    pc_online = (now - pc_last_seen) <= PC_TIMEOUT_SECONDS
                    if pc_online and not pc_was_online:
                        logger.info("PC is back online")
                        activity_data["pc_status"] = True
                        await main_processor.handle_activity_update(activity_data)
                        await notify_clients(activity_data)
                    elif not pc_online and pc_was_online:
                        logger.info("PC is offline")
                        activity_data["pc_status"] = False
                        await main_processor.handle_activity_update(activity_data)
                        await notify_clients(activity_data)
                    pc_was_online = pc_online

            logger.info("Spawning PC monitor loop...")
            asyncio.create_task(monitor_pc_status())