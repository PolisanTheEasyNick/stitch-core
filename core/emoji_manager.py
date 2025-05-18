import json
import random
from pathlib import Path

DEFAULT_EMOJIS_FILE = Path("/data/default_emojis.json")

def load_default_emojis():
    if not DEFAULT_EMOJIS_FILE.exists():
        return []
    with open(DEFAULT_EMOJIS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_default_emojis(emojis):
    with open(DEFAULT_EMOJIS_FILE, "w", encoding="utf-8") as f:
        json.dump(emojis, f, ensure_ascii=False, indent=2)

def get_random_default_emoji():
    emojis = load_default_emojis()
    if not emojis:
        return TG_DEFAULT_EMOJI
    return int(random.choice(emojis))

def add_default_emoji(emoji: str):
    emojis = load_default_emojis()
    emojis.append(emoji)
    save_default_emojis(emojis)

def remove_default_emoji(index: int):
    emojis = load_default_emojis()
    if 0 <= index < len(emojis):
        emojis.pop(index)
        save_default_emojis(emojis)
