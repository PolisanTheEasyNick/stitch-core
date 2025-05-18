from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
import requests
import json
import datetime
import pytz
from time import sleep
import asyncio
import websockets
from bs4 import BeautifulSoup

from .base import APIModule
from core.config import STEAM_PROFILE_LINK, STEAM_API, STEAM_USER
from core.main_processor import main_processor

connected_clients = set()
status = {}

async def send_update(data):
    global connected_clients
    disconnected = set()
    message = json.dumps(data)
    for ws in connected_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    connected_clients -= disconnected


def steam_info():
  #response = requests.get(f'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={STEAM_API}&steamids={STEAM_USER}')
  #if response:
  #  return response.json()
  response = requests.get(STEAM_PROFILE_LINK)
  soup = BeautifulSoup(response.text, 'html.parser')
  element = soup.find(class_="profile_in_game_header")
  text = ""
  if element:
    text = element.get_text()
  if text == "Currently Offline":
    return {"status": "offline"}
  elif text == "Currently Online":
    return {"status": "online"}
  elif text == "Currently In-Game":
    game_name = soup.find(class_="profile_in_game_name").get_text().strip()
    return {"status": "playing", "game_name": game_name}
  else:
    return {"status": "error"}

async def steam_update():
    global status
    while True:
        prev_status = status
        status = steam_info()
        if status == prev_status:
          await asyncio.sleep(20)
          continue

        if status["status"] == "playing":
            await main_processor.handle_steam_update(status["game_name"], True)
        else:
            await main_processor.handle_steam_update("", False)

        await asyncio.sleep(20)

class SteamModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:

        @router.get("/steam")
        def get_steam():
            return status

    def register_websockets(self, app: FastAPI):
        @app.websocket("/steam")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            connected_clients.add(websocket)

            try:
                await websocket.send_json(status)
            except WebSocketDisconnect:
                connected_clients.remove(websocket)

    def register_events(self, app: FastAPI) -> None:
        @app.on_event("startup")
        async def start_steam_update():
            asyncio.create_task(steam_update())
