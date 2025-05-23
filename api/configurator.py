from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Optional


from core.quote_manager import (
    load_quotes, save_quotes,
    append_quote, update_quote, remove_quote
)
from core.emoji_manager import (
    load_emojis, save_emojis,
    append_emoji, update_emoji, remove_emoji,
    parse_emoji_kind
)
from api.base import APIModule
from core.config import IP_WHITELIST

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


def validate(request):
    client_ip = get_real_ip(request)
    if client_ip not in IP_WHITELIST:
        raise HTTPException(status_code=403, detail=f"Forbidden: IP {client_ip} not allowed")

class ConfigAPI(APIModule):
    def register_routes(self, router: APIRouter) -> None:

        # QUOTES

        @router.get("/config/quotes", response_model=List[str])
        async def get_quotes(request: Request):
            validate(request)
            return load_quotes()

        @router.post("/config/quotes")
        async def set_quotes(request: Request, payload: QuotesPayload):
            validate(request)
            if not all(isinstance(q, str) and q.strip() for q in payload.quotes):
                raise HTTPException(400, detail="Quotes must be non-empty strings.")
            save_quotes(payload.quotes)
            return {"success": True, "count": len(payload.quotes)}

        @router.patch("/config/quotes/add")
        async def add_quote(request: Request, payload: EmojiAddPayload):
            validate(request)
            append_quote(payload.value)
            return {"success": True}

        @router.patch("/config/quotes/edit")
        async def edit_quote(request: Request, payload: QuoteEditPayload):
            validate(request)
            update_quote(payload.index, payload.value)
            return {"success": True}

        @router.delete("/config/quotes/{index}")
        async def delete_quote(request: Request, index: int):
            validate(request)
            remove_quote(index)
            return {"success": True}

        # EMOJIS

        @router.get("/config/emoji", response_model=List[str])
        async def get_emojis(request: Request, type: Optional[str] = Query("default")):
            validate(request)
            kind = parse_emoji_kind(type)
            return load_emojis(kind)

        @router.post("/config/emoji")
        async def set_emojis(request: Request, payload: EmojisPayload, type: Optional[str] = Query("default")):
            validate(request)
            kind = parse_emoji_kind(type)
            if not all(isinstance(e, str) and e.strip() for e in payload.emojis):
                raise HTTPException(400, detail="Emojis must be non-empty strings.")
            save_emojis(payload.emojis, kind)
            return {"success": True, "count": len(payload.emojis)}

        @router.patch("/config/emoji/add")
        async def add_emoji(request: Request, payload: EmojiAddPayload, type: Optional[str] = Query("default")):
            validate(request)
            kind = parse_emoji_kind(type)
            append_emoji(payload.value, kind)
            return {"success": True}

        @router.patch("/config/emoji/edit")
        async def edit_emoji(request: Request, payload: EmojiEditPayload, type: Optional[str] = Query("default")):
            validate(request)
            kind = parse_emoji_kind(type)
            update_emoji(payload.index, payload.value, kind)
            return {"success": True}

        @router.delete("/config/emoji/{index}")
        async def delete_emoji(request: Request, index: int, type: Optional[str] = Query("default")):
            validate(request)
            kind = parse_emoji_kind(type)
            remove_emoji(index, kind)
            return {"success": True}

    def register_websockets(self, router: APIRouter) -> None:
        pass

    def register_events(self, app) -> None:
        pass
