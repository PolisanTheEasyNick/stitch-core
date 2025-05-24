from fastapi import APIRouter, Request
import asyncio

from .base import APIModule
from core import quote_manager
from core.logger import get_logger

logger = get_logger("Quotes")

class QuoteModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:

        @router.get("/quote")
        async def get_random_quote(request: Request):
            logger.debug("GET on /quote")
            return {"quote": quote_manager.get_random_quote()}


