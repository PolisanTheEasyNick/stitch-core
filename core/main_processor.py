from typing import Optional
import asyncio

from .config import TG_IS_PREMIUM, PILED_DEFAULT_COLOR
from .telegram import TelegramAPI
from .piled import send_color_request, set_default_color
from .game_manager import find_game_by_query


class MainProcessor:
    def __init__(self):
        self.current_spotify_song = None
        self.is_playing_game = False
        self.is_playing_osu = False
        self.bio_limit = 140 if TG_IS_PREMIUM else 70

    async def set_default_status(self):
        #from any game state to default
        if self.current_spotify_song:
            await TelegramAPI.set_status_text(self.current_spotify_song)
        else:
            await TelegramAPI.set_default_status()

    async def set_current_emoji(self):
        #may be some game, or activity, or low battery, or just random from defaults
        if self.is_playing_game or self.is_playing_osu:
            return #steam or osu processors should've set own emoji
        await TelegramAPI.set_default_emoji()
        #currently method is simple, but will be enhanced

    async def handle_spotify_update(self, song: str, artist: str, is_playing: bool, is_local: bool, is_stopped: bool = False):
        """Called by the Spotify API module on new song/event."""
        if self.is_playing_game or self.is_playing_osu:
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

        if self.is_playing_osu:
            return

        if is_playing_game:
            await TelegramAPI.set_status_text("🎮: " + game_name)

            game = find_game_by_query(game_name)
            emoji_id = game["emoji_id"] if game else find_game_by_query("default game icon")["emoji_id"]

            await TelegramAPI.set_status_emoji(emoji_id)
            color = game["color"]
            if color.startswith("#"):
                color = color[1:]

            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            send_color_request(r, g, b)
        else:
            await self.set_default_status()
            await self.set_current_emoji()
            set_default_color()

    async def handle_osu_update(self, osu_data: str):
        artist = osu_data["artist"]
        title = osu_data["title"]
        BPM = osu_data["BPM"]
        SR = osu_data["SR"]
        STATUS = osu_data["status"]
        print(f"Received osu update: {artist} - {title}, BPM: {BPM}, SR: {SR}, Status: {STATUS}")
        if STATUS == 2:
            gameBio = f"🎮osu!: {artist} - {title} | 🥁: {BPM} | {SR}*"
        elif STATUS == 11:
            gameBio = f"🎮osu!: Searching for multiplayer lobby"
        elif STATUS == 12:
            gameBio = f"🎮osu!: Chilling in multiplayer lobby"
        elif STATUS == 3 or STATUS == -1:
            self.is_playing_osu = False
            await self.set_default_status()
            await self.set_current_emoji()
            set_default_color()
            return
        else:
            gameBio = f"🎮osu!: Chilling in main menu"
        await TelegramAPI.set_status_text(gameBio)
        if not self.is_playing_osu:
            self.is_playing_osu = True
            game = find_game_by_query("osu")
            emoji_id = game["emoji_id"] if game else find_game_by_query("default game icon")["emoji_id"]
            await TelegramAPI.set_status_emoji(emoji_id)
            color = game["color"]
            if color.startswith("#"):
                color = color[1:]
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            send_color_request(r, g, b)


main_processor = MainProcessor()
