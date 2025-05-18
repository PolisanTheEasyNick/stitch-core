from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from .base import APIModule
from core.main_processor import main_processor

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

async def spotify_update():
    global last_spotify
    old_artist = None
    old_song = None

    while True:
        try:
            data = get_info()
        except Exception as e:
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
            old_artist, old_song = artist, song
            await main_processor.handle_spotify_update(song, artist, is_playing, is_local)
            await broadcast_update()

        await asyncio.sleep(5)

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
            return last_spotify

    def register_websockets(self, app: FastAPI):
        @app.websocket("/spotify")
        async def websocket_endpoint(websocket: WebSocket):
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
