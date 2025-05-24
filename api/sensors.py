from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
import asyncio
import json

from .base import APIModule, get_real_ip
from core.config import IP_WHITELIST
from core.logger import get_logger

logger = get_logger("Sensors")

latest_sensor_data = {
    "temperature": None,
    "pressure": None,
    "humidity": None,
    "co2": None
}

connected_clients = set()

ALLOWED_IPS = IP_WHITELIST

async def notify_clients(data):
    logger.debug("Notifying WS clients about update")
    global connected_clients
    alive = set()
    for ws in connected_clients:
        try:
            await ws.send_json(data)
            alive.add(ws)
        except Exception:
            pass
    connected_clients = alive

class SensorsModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:
        @router.post("/sensors")
        async def update_sensors(request: Request):
            logger.debug("POST on /sensors")
            client_ip = get_real_ip(request)
            if client_ip not in ALLOWED_IPS:
                logger.warning(f"POST on /sensors from non-whitelisted IP: {client_ip}")
                raise HTTPException(status_code=403, detail=f"Forbidden: IP {client_ip} not allowed")

            global latest_sensor_data
            incoming = await request.json()

            updated = False
            for key in latest_sensor_data:
                if key in incoming:
                    latest_sensor_data[key] = incoming[key]
                    updated = True

            if updated:
                await notify_clients(latest_sensor_data)

            return {"status": "ok"}

        @router.get("/sensors")
        async def get_sensors():
            logger.debug("GET on /sensors")
            return latest_sensor_data

    def register_websockets(self, app: FastAPI):
        @app.websocket("/sensors")
        async def sensors_ws(websocket: WebSocket):
            await websocket.accept()
            connected_clients.add(websocket)
            try:
                await websocket.send_json(latest_sensor_data)
            except WebSocketDisconnect:
                connected_clients.remove(websocket)
