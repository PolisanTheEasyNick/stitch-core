from typing import Optional
import asyncio

from .config import TG_IS_PREMIUM
from .telegram import TelegramAPI

#TODO: REWRITE AS CONFIGURATOR
games_emoji_list = {
    "osu": (5238084986841607939,),
    "977950": ("A Dance of Fire and Ice", 5235672984747779211),
    "1091500": ("Cyberpunk 2077", 5244454474881180648),
    "730": ("Counter-Strike 2", 5242547097084897042),
    "33230": ("Assassin's Creed II", 5242331923518332969),
    "48190": ("Assassin's Creed Brotherhood", 5242331923518332969),
    "201870": ("Assassin's Creed Revelations", 5242331923518332969),
    "911400": ("Assassin's Creed III Remastered", 5242331923518332969),
    "289650": ("Assassin's Creed Unity", 5242331923518332969),
    "368500": ("Assassin's Creed Syndicate", 5242331923518332969),
    "812140": ("Assassin's Creed Odyssey", 5242331923518332969),
    "311560": ("Assassin's Creed Rogue", 5242331923518332969),
    "1245620": ("ELDEN RING", 5247083299809009542),
    "20900": ("The Witcher: Enhanced Edition", 5402292448539978864),
    "20920": ("The Witcher 2: Assassins of Kings Enhanced Edition", 5276175256493503130),
    "292030": ("The Witcher 3: Wild Hunt", 5247031932000149461),
    "400": ("Portal", 5328109481345690460),
    "620": ("Portal 2", 5328109481345690460),
    "2012840": ("Portal with RTX", 5328109481345690460),
    "1113560": ("NieR Replicant ver.1.22474487139...", 5274055672953054735),
    "524220": ("NieR: Automata", 5274055672953054735),
    "244210": ("Assetto Corsa", 5224687128419511287),
    "805550": ("Assetto Corsa Competizione", 5224687128419511287),
    "1174180": ("Red Dead Redemption 2", 5400083783082845798),
    "275850": ("No Man's Sky", 5402372098708481565),
    "990080": ("Hogwarts Legacy", 5402498941977634892),
    "70": ("Half-Life", 5402386138956573252),
    "220": ("Half-Life 2", 5402386138956573252),
    "380": ("Half-Life 2: Episode One", 5402386138956573252),
    "420": ("Half-Life 2: Episode Two", 5402386138956573252),
    "340": ("Half-Life 2: Lost Coast", 5402386138956573252),
    "320": ("Half-Life 2: Deathmatch", 5402386138956573252),
    "130": ("Half-Life: Blue Shift", 5402386138956573252),
    "360": ("Half-Life Deathmatch: Source", 5402386138956573252),
    "50": ("Half-Life: Opposing Force", 5402386138956573252),
    "280": ("Half-Life: Source", 5402386138956573252),
    "322170": ("Geometry Dash", 5402191259110484152),
    "227300": ("Euro Truck Simulator 2", 5402444434547679717),
    "1850570": ("DEATH STRANDING DIRECTOR'S CUT", 5402127916932801115),
    "1190460": ("DEATH STRANDING", 5402127916932801115),
    "870780": ("Control Ultimate Edition", 5402430304105275959),
    "493490": ("City Car Driving", 5402374224717291970),
    "1782380": ("SCP: Containment Breach Multiplayer", 5222479781517342513),
    "4500": ("S.T.A.L.K.E.R.: Shadow of Chernobyl", 5426959893124884146),
    "20510": ("S.T.A.L.K.E.R.: Clear Sky", 5426959893124884146),
    "41700": ("S.T.A.L.K.E.R.: Call of Pripyat", 5426959893124884146),
    "1643320": ("S.T.A.L.K.E.R. 2: Heart of Chornobyl", 5426959893124884146),
    "570940": ("DARK SOULS™: REMASTERED", 5433797867607180465),
    "335300": ("DARK SOULS™ II: Scholar of the First Sin", 5433797867607180465),
    "374320": ("DARK SOULS™ III", 5433797867607180465),
    "814380": ("Sekiro™: Shadows Die Twice", 5418100573889117350),
    "": ("default game icon", 5244764300937011946)
}


def get_game(key):
    key = key.strip()
    for game_id, game_info in games_emoji_list.items():
      if game_info[0] == key:
        return game_id
      elif game_id == key:
        return game_info[-1]
    return None

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
            emoji_id = get_game(game_name)
            if not emoji_id:
                emoji_id = get_game("")
            await TelegramAPI.set_status_emoji(emoji_id)
        else:
            await self.set_default_status()
            await self.set_current_emoji()

    async def handle_osu_update(self, osu_data: str):
        artist = osu_data["artist"]
        title = osu_data["title"]
        BPM = osu_data["BPM"]
        SR = osu_data["SR"]
        STATUS = osu_data["status"]
        if STATUS == 2:
            gameBio = f"🎮osu!: {artist} - {title} | 🥁: {BPM} | {SR}*"
        elif STATUS == 11:
            gameBio = f"🎮osu!: Searching for multiplayer lobby"
        elif STATUS == 12:
            gameBio = f"🎮osu!: Chilling in multiplayer lobby"
        elif STATUS == 3 or STATUS == -1: #game shutdown animation
            self.is_playing_osu = False
            await self.set_default_status()
            await self.set_current_emoji()
            return
        else:
            gameBio = f"🎮osu!: Chilling in main menu"
        await TelegramAPI.set_status_text(gameBio)
        await TelegramAPI.set_status_emoji(5238084986841607939)
        self.is_playing_osu = True

main_processor = MainProcessor()
