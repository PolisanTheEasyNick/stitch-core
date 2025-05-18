from dotenv import load_dotenv
import os

load_dotenv("config.env")

DIGEST_BEARER = os.getenv("DIGEST_BEARER", "")
IP_WHITELIST = os.getenv("IP_WHITELIST", "").split(",")

ACCUWEATHER_API_KEY = os.getenv("ACCUWEATHER_API_KEY", "")
ACCUWEATHER_LOCATION_CODE = os.getenv("ACCUWEATHER_LOCATION_CODE", "")

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
WEATHER_COORDS = os.getenv("WEATHER_COORDS", "")

STEAM_API = os.getenv("STEAM_API", "")
STEAM_USER = os.getenv("STEAM_USER", "")
STEAM_PROFILE_LINK = os.getenv("STEAM_PROFILE_LINK", "")

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID", "")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "")

TG_API_KEY = os.getenv("TG_API_KEY", "")
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_IS_PREMIUM = os.getenv("TG_IS_PREMIUM", False) == "True"
TG_DEFAULT_STATUS = os.getenv("TG_DEFAULT_STATUS", "")
TG_DEFAULT_EMOJI=os.getenv("TG_DEFAULT_EMOJI", 5260623257224110661)