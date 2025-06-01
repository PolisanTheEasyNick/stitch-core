from typing import Optional
import asyncio

from .config import TG_IS_PREMIUM, PILED_DEFAULT_COLOR, HOSTNAME, TG_DEFAULT_EMOJI, TG_CYCLING_EMOJI, TG_LOWBATTERY_EMOJI
from .telegram import TelegramAPI
from .piled import send_color_request, set_default_color
from .game_manager import find_game_by_query
from .logger import get_logger
from .enums import ActivityType

logger = get_logger("MainProcessor")


class MainProcessor:
    def __init__(self):
        self.current_spotify_song = None
        self.is_playing_game = False
        self.is_playing_osu = False
        self.bio_limit = 140 if TG_IS_PREMIUM else 70
        self.wearos_activity = None
        self.phone_activity = None

    async def get_emoji_id_by_activity(activity: ActivityType) -> Optional[str]:
        if activity == ActivityType.CYCLING:
            return 5316848390628187649
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://{HOSTNAME}/emoji?type={activity.value}")
                if response.status_code == 200:
                    return response.json().get("emoji")
        except Exception as e:
            logger.warning(f"Failed to get emoji for {activity.value}: {e}")
        return TG_DEFAULT_EMOJI

    async def set_default_status(self):
        #from any game state to default
        if self.current_spotify_song:
            logger.debug("Setting Spotify song status")
            await TelegramAPI.set_status_text(self.current_spotify_song)
        else:
            logger.debug("Setting default TG status")
            await TelegramAPI.set_default_status()

    async def set_current_emoji(self):
        logger.debug("Setting current emoji")
        if self.is_playing_game or self.is_playing_osu:
            #steam or osu! should set it.
            return

        #checking whether battery low

        if self.wearos_activity == "WALKING":
            emoji_id = await get_emoji_id_by_activity(ActivityType.WALKING)
        elif self.wearos_activity == "SLEEPING":
            emoji_id = await get_emoji_id_by_activity(ActivityType.SLEEPING)
        elif self.wearos_activity == "CYCLING":
            emoji_id = TG_CYCLING_EMOJI
        elif self.phone_activity == "WALKING":
            emoji_id = await get_emoji_id_by_activity(ActivityType.WALKING)
        elif self.phone_activity == "SLEEPING":
            emoji_id = await get_emoji_id_by_activity(ActivityType.SLEEPING)
        elif self.phone_activity == "CYCLING":
            emoji_id = TG_CYCLING_EMOJI
        else:
            emoji_id = None

        if emoji_id:
            logger.debug(f"Activity-based emoji selected: {emoji_id}")
            await TelegramAPI.set_status_emoji(emoji_id)
        else:
            await TelegramAPI.set_default_emoji()

    async def handle_spotify_update(self, song: str, artist: str, is_playing: bool, is_local: bool, is_stopped: bool = False):
        """Called by the Spotify API module on new song/event."""
        logger.debug("New spotify update")
        if self.is_playing_game or self.is_playing_osu:
            logger.debug("Skipping Spotify status update because a game is running")
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
        logger.debug(f"Sending status to TG: {status}")
        await TelegramAPI.set_status_text(status)


    async def handle_steam_update(self, game_name: str, is_playing_game: bool):
        """Called by the Steam API module."""
        logger.debug(f"Steam update called")
        self.is_playing_game = is_playing_game

        if self.is_playing_osu:
            return

        if is_playing_game:
            await TelegramAPI.set_status_text("🎮: " + game_name)

            game = find_game_by_query(game_name)
            emoji_id = game["emoji_id"] if game else find_game_by_query("default game icon")["emoji_id"]
            logger.debug(f"Emoji_id: {emoji_id}")
            await TelegramAPI.set_status_emoji(emoji_id)
            color = game["color"]
            if color.startswith("#"):
                color = color[1:]
            logger.debug(f"Game: {game}, emoji: {emoji_id}, color: {color}")
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
        logger.debug(f"Received osu update: {artist} - {title}, BPM: {BPM}, SR: {SR}, Status: {STATUS}")
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

    async def handle_activity_update(self, activity_data: dict):
        phone_battery = activity_data.get("phone_battery")
        wearos_battery = activity_data.get("wearos_battery")
        self.phone_activity = activity_data.get("phone_activity", "CHILL")
        self.wearos_activity = activity_data.get("wearos_activity", "CHILL")

        logger.debug(f"Handling activity update: {activity_data}")
        set_current_emoji()




main_processor = MainProcessor()
