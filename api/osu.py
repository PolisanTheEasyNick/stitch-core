from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
import asyncio
import json

from .base import APIModule, get_real_ip
from core.config import IP_WHITELIST
from core.main_processor import main_processor
from core.logger import get_logger

logger = get_logger("OSU")

latest_osu_data = {
    "artist": None,
    "title": None,
    "BPM": None,
    "SR": None,
    "status": None #Status should be 3 or -1 when osu shutted down.
}

connected_clients = set()

ALLOWED_IPS = IP_WHITELIST

async def notify_clients(data):
    logger.debug("Notifying WS clients about change")
    global connected_clients
    alive = set()
    for ws in connected_clients:
        try:
            await ws.send_json(data)
            alive.add(ws)
        except Exception:
            pass
    connected_clients = alive

class OsuModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:
        @router.post("/osu")
        async def update_osu(request: Request):
            logger.debug("POST on /osu")
            client_ip = get_real_ip(request)
            if client_ip not in ALLOWED_IPS:
                raise HTTPException(status_code=403, detail=f"Forbidden: IP {client_ip} not allowed")

            global latest_osu_data
            incoming = await request.json()

            updated = False
            for key in latest_osu_data:
                if key in incoming:
                    latest_osu_data[key] = incoming[key]
                    updated = True

            if updated:
                logger.info("New change, notifying clients")
                await notify_clients(latest_osu_data)
                await main_processor.handle_osu_update(latest_osu_data)

            return {"status": "ok"}

        @router.get("/osu")
        async def get_osu():
            logger.debug("GET on /osu")
            return latest_osu_data

    def register_websockets(self, app: FastAPI):
        @app.websocket("/osu")
        async def osus_ws(websocket: WebSocket):
            await websocket.accept()
            connected_clients.add(websocket)
            try:
                await websocket.send_json(latest_osu_data)
            except WebSocketDisconnect:
                connected_clients.remove(websocket)
