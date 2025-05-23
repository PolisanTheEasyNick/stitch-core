from fastapi import APIRouter, Request, Query
import asyncio

from .base import APIModule
from core import emoji_manager

class EmojiModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:

        @router.get("/emoji")
        async def get_random_emoji(request: Request, type: str = Query("default")):
            kind = emoji_manager.parse_emoji_kind(type)
            emoji = emoji_manager.get_random_emoji(kind)
            return {"emoji": emoji, "type": kind.value}


