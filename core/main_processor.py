from typing import Optional
import asyncio

from .config import TG_IS_PREMIUM
from .telegram import TelegramAPI

class MainProcessor:
    def __init__(self):
        self.current_spotify_song = None
        self.is_playing_game = False
        self.bio_limit = 140 if TG_IS_PREMIUM else 70

    async def handle_spotify_update(self, song: str, artist: str, is_playing: bool, is_local: bool, is_stopped: bool = False):
        """Called by the Spotify API module on new song/event."""
        if self.is_playing_game:
            #print("Skipping Spotify status update because a game is running")
            return

        if is_stopped:
            await TelegramAPI.set_default_status()
            self.current_spotify_song = None
            return

        prefix = "🎧:"
        suffix = ""
        if is_local:
            suffix += " [LOCAL]"
        if not is_playing:
            suffix += " [PAUSED]"

        full = f"{prefix} {artist} - {song}{suffix}"
        song_only = f"{prefix} {song}{suffix}"

        if len(full) <= self.bio_limit:
            status = full
        elif len(song_only) <= self.bio_limit:
            status = song_only
        else:
            max_song_len = self.bio_limit - len(prefix + suffix) - 1
            trimmed_song = song[:max_song_len - 3] + "..." if max_song_len > 3 else "..."
            status = f"{prefix} {trimmed_song}{suffix}"

        self.current_spotify_song = status
        await TelegramAPI.set_status_text(status)

    async def handle_steam_update(self, game_name: str, is_playing_game: bool):
        """Called by the Steam API module."""
        self.is_playing_game = is_playing_game

        if is_playing_game:
            self.is_playing_game = True
            await TelegramAPI.set_status_text("🎮: " + game_name)
        elif self.current_spotify_song:
            self.is_playing_game = False
            await TelegramAPI.set_status_text(self.current_spotify_song)
        else:
            self.is_playing_game = False


main_processor = MainProcessor()
