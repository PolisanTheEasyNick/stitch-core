from fastapi import APIRouter, Query
from typing import Optional
import httpx
from yt_finder import YoutubeSearch

from .base import APIModule

class AlbumArtModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:
        @router.get("/album")
        async def get_album(
            song: str = Query(...),
            artist: Optional[str] = Query(None)
        ):
            query = f"{artist} - {song}" if artist else song
            search = YoutubeSearch(query, max_results=1, language="en", region="US")
            videos = await search.search()
            return {"album_art_url": videos[0].thumbnails[-1]}
