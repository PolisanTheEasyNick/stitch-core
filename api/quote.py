from fastapi import APIRouter, Request
import asyncio

from .base import APIModule
from core import quote_manager

class QuoteModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:

        @router.get("/quote")
        async def get_random_quote(request: Request):
            return {"quote": quote_manager.get_random_quote()}


