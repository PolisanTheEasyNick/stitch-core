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

#TODO: REWRITE AS CONFIGURATOR
games_emoji_list = {
    "osu": (5238084986841607939,),
    "977950": ("A Dance of Fire and Ice", 5235672984747779211),
    "1091500": ("Cyberpunk 2077", 5244454474881180648),
    "730": ("Counter-Strike 2", 5242547097084897042),
    "33230": ("Assassin's Creed II", 5242331923518332969),
    "48190": ("Assassin's Creed Brotherhood", 5242331923518332969),
    "201870": ("Assassin's Creed Revelations", 5242331923518332969),
    "911400": ("Assassin's Creed III Remastered", 5242331923518332969),
    "289650": ("Assassin's Creed Unity", 5242331923518332969),
    "368500": ("Assassin's Creed Syndicate", 5242331923518332969),
    "812140": ("Assassin's Creed Odyssey", 5242331923518332969),
    "311560": ("Assassin's Creed Rogue", 5242331923518332969),
    "1245620": ("ELDEN RING", 5247083299809009542),
    "20900": ("The Witcher: Enhanced Edition", 5402292448539978864),
    "20920": ("The Witcher 2: Assassins of Kings Enhanced Edition", 5276175256493503130),
    "292030": ("The Witcher 3: Wild Hunt", 5247031932000149461),
    "400": ("Portal", 5328109481345690460),
    "620": ("Portal 2", 5328109481345690460),
    "2012840": ("Portal with RTX", 5328109481345690460),
    "1113560": ("NieR Replicant ver.1.22474487139...", 5274055672953054735),
    "524220": ("NieR: Automata", 5274055672953054735),
    "244210": ("Assetto Corsa", 5224687128419511287),
    "805550": ("Assetto Corsa Competizione", 5224687128419511287),
    "1174180": ("Red Dead Redemption 2", 5400083783082845798),
    "275850": ("No Man's Sky", 5402372098708481565),
    "990080": ("Hogwarts Legacy", 5402498941977634892),
    "70": ("Half-Life", 5402386138956573252),
    "220": ("Half-Life 2", 5402386138956573252),
    "380": ("Half-Life 2: Episode One", 5402386138956573252),
    "420": ("Half-Life 2: Episode Two", 5402386138956573252),
    "340": ("Half-Life 2: Lost Coast", 5402386138956573252),
    "320": ("Half-Life 2: Deathmatch", 5402386138956573252),
    "130": ("Half-Life: Blue Shift", 5402386138956573252),
    "360": ("Half-Life Deathmatch: Source", 5402386138956573252),
    "50": ("Half-Life: Opposing Force", 5402386138956573252),
    "280": ("Half-Life: Source", 5402386138956573252),
    "322170": ("Geometry Dash", 5402191259110484152),
    "227300": ("Euro Truck Simulator 2", 5402444434547679717),
    "1850570": ("DEATH STRANDING DIRECTOR'S CUT", 5402127916932801115),
    "1190460": ("DEATH STRANDING", 5402127916932801115),
    "870780": ("Control Ultimate Edition", 5402430304105275959),
    "493490": ("City Car Driving", 5402374224717291970),
    "1782380": ("SCP: Containment Breach Multiplayer", 5222479781517342513),
    "4500": ("S.T.A.L.K.E.R.: Shadow of Chernobyl", 5426959893124884146),
    "20510": ("S.T.A.L.K.E.R.: Clear Sky", 5426959893124884146),
    "41700": ("S.T.A.L.K.E.R.: Call of Pripyat", 5426959893124884146),
    "1643320": ("S.T.A.L.K.E.R. 2: Heart of Chornobyl", 5426959893124884146),
    "570940": ("DARK SOULS™: REMASTERED", 5433797867607180465),
    "335300": ("DARK SOULS™ II: Scholar of the First Sin", 5433797867607180465),
    "374320": ("DARK SOULS™ III", 5433797867607180465),
    "814380": ("Sekiro™: Shadows Die Twice", 5418100573889117350),
    "": ("default game icon", 5244764300937011946)
}

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

def get_game(key):
    key = key.strip()
    for game_id, game_info in games_emoji_list.items():
      if game_info[0] == key:
        return game_id
      elif game_id == key:
        return game_info[-1]
    return None

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
    game_name = soup.find(class_="profile_in_game_name").get_text()
    game_id = get_game(game_name)
    steam_info = {
      "response": {
        "players": [
            {
              "gameid": game_id,
              "gameextrainfo": game_name
            }
          ]
      }
    }

    return steam_info
  else:
    return {"status": "error"}

async def steam_update():
    global status
    while True:
        status = steam_info()

        if "status" in status:
            await main_processor.handle_steam_update("", False)
        elif "response" in status:
            players = status.get("response", {}).get("players", [])
            if players and "gameextrainfo" in players[0]:
                game_name = players[0]["gameextrainfo"]
                await main_processor.handle_steam_update(game_name, False)
            else:
                await main_processor.handle_steam_update("", False)
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
