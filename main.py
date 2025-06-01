import importlib
import pkgutil

from fastapi import FastAPI, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware


from api.base import APIModule
from core.config import HOSTNAME
from core.telegram import TelegramAPI



def load_modules() -> list[APIModule]:
    modules = []
    for finder, name, _ in pkgutil.iter_modules(["api"]):
        if name == "base":
            continue

        full_name = f"api.{name}"
        module = importlib.import_module(full_name)

        for attr in dir(module):
            obj = getattr(module, attr)
            if isinstance(obj, type) and issubclass(obj, APIModule) and obj is not APIModule:
                instance = obj()
                modules.append(instance)
    return modules

def create_app() -> FastAPI:
    app = FastAPI()
    main_router = APIRouter()

    for module in load_modules():
        module.register_routes(main_router)
        module.register_websockets(main_router)
        module.register_events(app)

    app.include_router(main_router)

    @app.get("/", response_class=HTMLResponse)
    async def list_routes():
        exclude_paths = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc", "/"}
        unique_paths = set()

        for route in app.routes:
            if hasattr(route, "path"):
                path = route.path
                if path not in exclude_paths and "{" not in path:
                    unique_paths.add(path)
        links = [f'<li><a href="{path}">{path}</a></li>' for path in sorted(unique_paths)]
        links_html = "\n".join(links)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Available Routes</title>
            <style>
                body {{ font-family: monospace; background: #1e1e1e; color: #eee; padding: 20px; }}
                a {{ color: #4fc3f7; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>Available Routes</h1>
            <ul>
                {links_html}
            </ul>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    app.add_middleware(
        CORSMiddleware,
        #allow_origins=[HOSTNAME],
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app



app = create_app()

### SILKSONG TOMORROW
import threading
from pathlib import Path
from datetime import datetime, timedelta
import random
import time
import json
import requests
import pytz
import asyncio
import os

async def silksong_trigger():
    await TelegramAPI.send_message(-1001172125765, "Silksong tomorrow!!")
    #await TelegramAPI.send_message(459839159, "Silksong tomorrow!!")

async def silksong_loop():
    cache_file = Path("/data/silksong")

    while True:
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Check cache to avoid repeating on the same day
        if cache_file.exists():
            try:
                with cache_file.open("r") as f:
                    cache_data = json.load(f)
                    if cache_data.get("last_sent") == today_str:
                        print("[Silksong] Already sent today, skipping.")
                        wait_minutes = random.randint(30, 90)
                        print(f"[Silksong] Checking again in {wait_minutes} minutes.")
                        await asyncio.sleep(wait_minutes * 60)
                        continue
            except Exception as e:
                print(f"[Silksong] Failed to read cache: {e}")

        # Pick a random time within the next 24 hours
        seconds_until_trigger = random.randint(0, 86400)
        print(f"[Silksong] Scheduled to trigger in {seconds_until_trigger // 3600}h {(seconds_until_trigger % 3600) // 60}m.")
        await asyncio.sleep(seconds_until_trigger)

        # Trigger and save date
        await silksong_trigger()
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with cache_file.open("w") as f:
                json.dump({"last_sent": today_str}, f)
            print("[Silksong] Cache updated.")
        except Exception as e:
            print(f"[Silksong] Failed to write cache: {e}")

        # Wait until tomorrow midnight
        now = datetime.now()
        next_day = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        seconds_until_tomorrow = (next_day - now).total_seconds()
        print(f"[Silksong] Sleeping until tomorrow ({seconds_until_tomorrow // 3600}h {(seconds_until_tomorrow % 3600) // 60}m).")
        await asyncio.sleep(seconds_until_tomorrow)

def start_silksong_task():
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(silksong_loop())
    else:
        threading.Thread(target=lambda: asyncio.run(silksong_loop()), daemon=True).start()

try:
    start_silksong_task()
except RuntimeError as e:
    print(f"[Silksong] Could not start silksong loop at init: {e}")
