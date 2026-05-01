import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

from core.quote_manager import (
    load_quotes,
    save_quotes,
    append_quote,
    update_quote,
    remove_quote,
)
from core.emoji_manager import (
    load_emojis,
    save_emojis,
    append_emoji,
    update_emoji,
    remove_emoji,
    parse_emoji_kind,
)
from core.game_manager import (
    load_games,
    save_games,
    append_game,
    update_game,
    remove_game,
)
from core.config import IP_WHITELIST
from core.data_paths import (
    DATA_DIR,
    EMOJI_FILES,
    GAMES_FILE,
    QUOTES_FILE,
    SPOTIFY_TOKEN_FILE,
    TELEGRAM_SESSION_FILE,
    USERBOT_SESSION_FILE,
    ensure_data_dir,
)
from core.telegram import TelegramAPI
from .base import APIModule, get_real_ip
from core.logger import get_logger

logger = get_logger("Configurator")


class QuotesPayload(BaseModel):
    quotes: List[str]


class QuoteEditPayload(BaseModel):
    index: int
    value: str


class EmojiEditPayload(BaseModel):
    index: int
    value: str


class EmojisPayload(BaseModel):
    emojis: List[str]


class EmojiAddPayload(BaseModel):
    value: str


class GameItem(BaseModel):
    steam_id: str
    name: str
    emoji_id: str
    color: str


class GamesPayload(BaseModel):
    games: List[GameItem]


class GameEditPayload(BaseModel):
    index: int
    game: GameItem


def validate(request):
    client_ip = get_real_ip(request)
    if client_ip not in IP_WHITELIST:
        raise HTTPException(status_code=403, detail=f"Forbidden: IP {client_ip} not allowed")


def _normalize_text_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _load_json_or_text_list(raw: bytes) -> list[str]:
    text = raw.decode("utf-8")
    stripped = text.strip()
    if stripped.startswith("[") or stripped.startswith("{"):
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            payload = payload.get("quotes") or payload.get("emojis") or payload.get("items")
        if not isinstance(payload, list):
            raise HTTPException(status_code=400, detail="Expected a JSON array or a supported object wrapper.")
        values = [str(item).strip() for item in payload if str(item).strip()]
    else:
        values = _normalize_text_lines(text)

    if not values:
        raise HTTPException(status_code=400, detail="No usable entries found in uploaded file.")
    return values


def _load_games_payload(raw: bytes) -> list[dict]:
    payload = json.loads(raw.decode("utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("games")
    if not isinstance(payload, list):
        raise HTTPException(status_code=400, detail="Games import expects a JSON array.")

    normalized = []
    for item in payload:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Each game entry must be a JSON object.")
        normalized.append(
            {
                "steam_id": str(item.get("steam_id", "")).strip(),
                "name": str(item.get("name", "")).strip(),
                "emoji_id": str(item.get("emoji_id", "")).strip(),
                "color": str(item.get("color", "#ffffff")).strip() or "#ffffff",
            }
        )

    if not normalized:
        raise HTTPException(status_code=400, detail="No games found in uploaded file.")
    return normalized


def _write_binary(path: Path, raw: bytes) -> None:
    ensure_data_dir()
    path.write_bytes(raw)


def _file_status(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }


class ConfigAPI(APIModule):
    def register_routes(self, router: APIRouter) -> None:
        @router.get("/config/import/status")
        async def get_import_status(request: Request):
            logger.debug("GET on /config/import/status")
            validate(request)
            return {
                "data_dir": str(DATA_DIR),
                "files": {
                    "quotes": _file_status(QUOTES_FILE),
                    "games": _file_status(GAMES_FILE),
                    "default_emojis": _file_status(EMOJI_FILES["default"]),
                    "ny_emojis": _file_status(EMOJI_FILES["ny"]),
                    "sleep_emojis": _file_status(EMOJI_FILES["sleep"]),
                    "walk_emojis": _file_status(EMOJI_FILES["walk"]),
                    "telegram_session": _file_status(TELEGRAM_SESSION_FILE),
                    "userbot_session": _file_status(USERBOT_SESSION_FILE),
                    "spotify_token": _file_status(SPOTIFY_TOKEN_FILE),
                },
            }

        @router.post("/config/import/quotes")
        async def import_quotes(request: Request, file: UploadFile = File(...)):
            logger.debug("POST on /config/import/quotes")
            validate(request)
            quotes = _load_json_or_text_list(await file.read())
            save_quotes(quotes)
            return {"success": True, "count": len(quotes)}

        @router.post("/config/import/emoji")
        async def import_emojis(request: Request, file: UploadFile = File(...), type: Optional[str] = Query("default")):
            logger.debug("POST on /config/import/emoji")
            validate(request)
            kind = parse_emoji_kind(type)
            emojis = _load_json_or_text_list(await file.read())
            save_emojis(emojis, kind)
            return {"success": True, "count": len(emojis), "type": kind.value}

        @router.post("/config/import/games")
        async def import_games(request: Request, file: UploadFile = File(...)):
            logger.debug("POST on /config/import/games")
            validate(request)
            games = _load_games_payload(await file.read())
            save_games(games)
            return {"success": True, "count": len(games)}

        @router.post("/config/import/telegram-session")
        async def import_telegram_session(request: Request, file: UploadFile = File(...)):
            logger.debug("POST on /config/import/telegram-session")
            validate(request)
            raw = await file.read()
            if not raw:
                raise HTTPException(status_code=400, detail="Uploaded session file is empty.")
            _write_binary(TELEGRAM_SESSION_FILE, raw)
            await TelegramAPI.reload_session()
            return {"success": True, "path": str(TELEGRAM_SESSION_FILE)}

        @router.post("/config/import/spotify-token")
        async def import_spotify_token(request: Request, file: UploadFile = File(...)):
            logger.debug("POST on /config/import/spotify-token")
            validate(request)
            raw = await file.read()
            if not raw:
                raise HTTPException(status_code=400, detail="Uploaded Spotify token file is empty.")
            _write_binary(SPOTIFY_TOKEN_FILE, raw)
            return {"success": True, "path": str(SPOTIFY_TOKEN_FILE)}

        @router.get("/config/quotes", response_model=List[str])
        async def get_quotes(request: Request):
            logger.debug("GET on /config/quotes")
            validate(request)
            return load_quotes()

        @router.post("/config/quotes")
        async def set_quotes(request: Request, payload: QuotesPayload):
            logger.debug("POST on /config/quotes")
            validate(request)
            if not all(isinstance(q, str) and q.strip() for q in payload.quotes):
                raise HTTPException(400, detail="Quotes must be non-empty strings.")
            save_quotes(payload.quotes)
            return {"success": True, "count": len(payload.quotes)}

        @router.patch("/config/quotes/add")
        async def add_quote(request: Request, payload: EmojiAddPayload):
            logger.debug("PATCH on /config/quotes/add")
            validate(request)
            append_quote(payload.value)
            return {"success": True}

        @router.patch("/config/quotes/edit")
        async def edit_quote(request: Request, payload: QuoteEditPayload):
            logger.debug("PATCH on /config/quotes/edit")
            validate(request)
            update_quote(payload.index, payload.value)
            return {"success": True}

        @router.delete("/config/quotes/{index}")
        async def delete_quote(request: Request, index: int):
            logger.debug(f"DELETE on /config/quotes/{index}")
            validate(request)
            remove_quote(index)
            return {"success": True}

        @router.get("/config/emoji", response_model=List[str])
        async def get_emojis(request: Request, type: Optional[str] = Query("default")):
            logger.debug("GET on /config/emoji")
            validate(request)
            kind = parse_emoji_kind(type)
            return load_emojis(kind)

        @router.post("/config/emoji")
        async def set_emojis(request: Request, payload: EmojisPayload, type: Optional[str] = Query("default")):
            logger.debug("POST on /config/emoji")
            validate(request)
            kind = parse_emoji_kind(type)
            if not all(isinstance(e, str) and e.strip() for e in payload.emojis):
                raise HTTPException(400, detail="Emojis must be non-empty strings.")
            save_emojis(payload.emojis, kind)
            return {"success": True, "count": len(payload.emojis)}

        @router.patch("/config/emoji/add")
        async def add_emoji(request: Request, payload: EmojiAddPayload, type: Optional[str] = Query("default")):
            logger.debug("PATCH on /config/emoji/add")
            validate(request)
            kind = parse_emoji_kind(type)
            append_emoji(payload.value, kind)
            return {"success": True}

        @router.patch("/config/emoji/edit")
        async def edit_emoji(request: Request, payload: EmojiEditPayload, type: Optional[str] = Query("default")):
            logger.debug("PATCH on /config/edit")
            validate(request)
            kind = parse_emoji_kind(type)
            update_emoji(payload.index, payload.value, kind)
            return {"success": True}

        @router.delete("/config/emoji/{index}")
        async def delete_emoji(request: Request, index: int, type: Optional[str] = Query("default")):
            logger.debug(f"DELETE on /config/emoji/{index}")
            validate(request)
            kind = parse_emoji_kind(type)
            remove_emoji(index, kind)
            return {"success": True}

        @router.get("/config/games", response_model=List[GameItem])
        async def get_games(request: Request):
            logger.debug("GET on /config/games")
            validate(request)
            return load_games()

        @router.post("/config/games")
        async def set_games(request: Request, payload: GamesPayload):
            logger.debug("POST on /config/games")
            validate(request)
            save_games([game.dict() for game in payload.games])
            return {"success": True, "count": len(payload.games)}

        @router.patch("/config/games/add")
        async def add_game(request: Request, payload: GameItem):
            logger.debug("PATCH on /config/games/add")
            validate(request)
            append_game(payload.dict())
            return {"success": True}

        @router.patch("/config/games/edit")
        async def edit_game(request: Request, payload: GameEditPayload):
            logger.debug("PATCH on /config/games/edit")
            validate(request)
            update_game(payload.index, payload.game.dict())
            return {"success": True}

        @router.delete("/config/games/{index}")
        async def delete_game(request: Request, index: int):
            logger.debug("DELETE on /config/games/{index}")
            validate(request)
            remove_game(index)
            return {"success": True}

    def register_websockets(self, router: APIRouter) -> None:
        pass

    def register_events(self, app) -> None:
        pass
