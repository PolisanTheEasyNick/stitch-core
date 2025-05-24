from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime

from .base import APIModule, get_real_ip
from core.main_processor import main_processor
from core.logger import get_logger
from core.config import IP_WHITELIST

logger = get_logger("Spotify")

last_spotify = {
    "artist": None,
    "song": None,
    "state": "stopped",
}

connected_clients: set[WebSocket] = set()

def get_info():
    cache_path = "/data/sp_token"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-read-playback-state", cache_path=cache_path))
    return sp.current_playback()

spotify_task = None
spotify_task_running = False
last_update = None

async def spotify_update():
    global last_spotify
    global spotify_task_running
    global last_update
    spotify_task_running = True
    old_artist = None
    old_song = None

    try:
        while spotify_task_running:
            try:
                data = get_info()
            except Exception as e:
                logger.warning(f"Error while getting info: {e}")
                last_spotify = {
                    "artist": None,
                    "song": None,
                    "state": "error",
                    "error": str(e),
                }
                await asyncio.sleep(10)
                continue

            if not data or not data.get("item"):
                last_spotify = {
                    "artist": None,
                    "song": None,
                    "state": "stopped",
                }
                logger.debug(f"No data")
                await main_processor.handle_spotify_update("", "", False, False, True)
                await broadcast_update()
                await asyncio.sleep(10)
                continue

            is_playing = data.get("is_playing", False)
            song = data["item"]["name"]
            is_local = data['item']['is_local']
            artist = ", ".join(a["name"] for a in data["item"]["artists"])

            if song != old_song or artist != old_artist or last_spotify.get("state") != ("playing" if is_playing else "paused"):

                last_spotify = {
                    "artist": artist,
                    "song": song,
                    "state": "playing" if is_playing else "paused",
                    "isLocal": is_local
                }
                last_update = datetime.utcnow().isoformat() + "Z"
                logger.debug(f"New data: {last_spotify}")
                old_artist, old_song = artist, song
                await main_processor.handle_spotify_update(song, artist, is_playing, is_local)
                await broadcast_update()

            await asyncio.sleep(5)
    finally:
        spotify_task_running = False
        last_spotify = {
            "artist": None,
            "song": None,
            "state": "stopped",
        }
        logger.debug(f"No data")
        await main_processor.handle_spotify_update("", "", False, False, True)
        await broadcast_update()

async def broadcast_update():
    to_remove = set()
    for ws in connected_clients:
        try:
            await ws.send_json(last_spotify)
        except WebSocketDisconnect:
            to_remove.add(ws)
    for ws in to_remove:
        connected_clients.remove(ws)

class SpotifyModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:
        @router.get("/spotify")
        def get_spotify():
            logger.debug(f"GET on /spotify")
            return last_spotify

        @router.get("/services/spotify/status")
        def get_spotify_status():
            return {
                "running": spotify_task_running,
                "name": "Spotify",
                "last_update": last_update or "never",
            }

        @router.post("/services/spotify/toggle")
        async def toggle_spotify_task(request: Request):
            client_ip = get_real_ip(request)
            if client_ip not in IP_WHITELIST:
                logger.warning(f"POST on /piled from non-whitelisted IP: {client_ip}")
                raise HTTPException(status_code=403, detail=f"Forbidden: IP {client_ip} not allowed")
            global spotify_task, spotify_task_running


            if spotify_task_running:
                logger.info("Spotify stopping per request from POST")
                # stop the task
                spotify_task_running = False
                if spotify_task:
                    spotify_task.cancel()
                    spotify_task = None
                return {"status": "stopped"}
            else:
                # start the task
                logger.info("Spotify starting per request from POST")
                spotify_task = asyncio.create_task(spotify_update())
                return {"status": "started"}


    def register_websockets(self, app: FastAPI):
        @app.websocket("/spotify")
        async def websocket_endpoint(websocket: WebSocket):
            logger.debug(f"GET on ws /spotify")
            await websocket.accept()
            connected_clients.add(websocket)
            try:
                await websocket.send_json(last_spotify)
            except WebSocketDisconnect:
                connected_clients.remove(websocket)

    def register_events(self, app: FastAPI) -> None:
        @app.on_event("startup")
        async def start_spotify_update():
            asyncio.create_task(spotify_update())
