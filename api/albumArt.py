from fastapi import APIRouter, Query
from typing import Optional
import httpx
from yt_finder import YoutubeSearch

from .base import APIModule
from core.logger import get_logger

logger = get_logger("AlbumArt")

class AlbumArtModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:
        @router.get("/album")
        async def get_album(
            song: str = Query(...),
            artist: Optional[str] = Query(None)
        ):
            query = f"{artist} - {song}" if artist else song
            logger.debug(f"Getting album art for {query}")
            search = YoutubeSearch(query, max_results=1, language="en", region="US")
            videos = await search.search()
            logger.debug(f"Found album art: {videos[0].thumbnails[-1]}")
            return {"album_art_url": videos[0].thumbnails[-1]}
