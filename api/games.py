from fastapi import APIRouter, Request, HTTPException, Query
from typing import Optional

from .base import APIModule
from core import game_manager
from core.logger import get_logger

logger = get_logger("Games")

class GameModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:

        @router.get("/games")
        async def get_game(request: Request, q: Optional[str] = Query(None, alias="query")):
            logger.debug("GET on /games")
            if not q:
                logger.error(f"No query parameter in request: {request}")
                raise HTTPException(status_code=400, detail="Query parameter is required")

            game = game_manager.find_game_by_query(q)
            if not game:
                logger.error(f"No game for query: {q}")
                raise HTTPException(status_code=404, detail="Game not found")

            return {
                "steam_id": game.get("steam_id"),
                "name": game.get("name"),
                "emoji_id": game.get("emoji_id"),
                "color": game.get("color")
            }
