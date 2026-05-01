from pathlib import Path
import os

DATA_DIR = Path("/data")
LEGACY_TMP_DIR = Path(os.getenv("LEGACY_TMP_DIR", "/legacy-tmp"))

QUOTES_FILE = DATA_DIR / "quotes.json"
GAMES_FILE = DATA_DIR / "games.json"
SPOTIFY_TOKEN_FILE = DATA_DIR / "sp_token"
TELEGRAM_SESSION_FILE = DATA_DIR / "Stitch.session"
USERBOT_SESSION_FILE = DATA_DIR / "userbot.session"
WEATHER_CACHE_FILE = DATA_DIR / "last_weather_fetch.txt"

EMOJI_FILES = {
    "default": DATA_DIR / "default_emojis.json",
    "ny": DATA_DIR / "ny_emojis.json",
    "sleep": DATA_DIR / "sleep_emojis.json",
    "walk": DATA_DIR / "walking_emojis.json",
}


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
