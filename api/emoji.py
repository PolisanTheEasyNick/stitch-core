from fastapi import APIRouter, Request, Query
import asyncio

from .base import APIModule
from core import emoji_manager
from core.logger import get_logger

logger = get_logger("Emoji")

class EmojiModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:

        @router.get("/emoji")
        async def get_random_emoji(request: Request, type: str = Query("default")):
            kind = emoji_manager.parse_emoji_kind(type)
            logger.debug(f"Got kind {kind} for query: {type}")
            emoji = emoji_manager.get_random_emoji(kind)
            logger.debug(f"GET random emoji on /emoji, returning {emoji} for {kind}")
            return {"emoji": emoji, "type": kind.value}


