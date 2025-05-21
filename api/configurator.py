from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from core.quote_manager import load_quotes, save_quotes
from api.base import APIModule

class QuotesPayload(BaseModel):
    quotes: List[str]

class ConfigAPI(APIModule):
    def register_routes(self, router: APIRouter) -> None:
        @router.get("/config/quotes", response_model=List[str])
        async def get_quotes():
            return load_quotes()

        @router.post("/config/quotes")
        async def update_quotes(payload: QuotesPayload):
            if not all(isinstance(q, str) and q.strip() for q in payload.quotes):
                raise HTTPException(status_code=400, detail="Quotes must be non-empty strings.")
            save_quotes(payload.quotes)
            return {"success": True, "count": len(payload.quotes)}

    def register_websockets(self, router: APIRouter) -> None:
        pass

    def register_events(self, app) -> None:
        pass
