import json
import random
from pathlib import Path
from datetime import date

from .config import TG_DEFAULT_EMOJI
from .enums import EmojiKind

EMOJI_FILES = {
    EmojiKind.DEFAULT: Path("/data/default_emojis.json"),
    EmojiKind.NY: Path("/data/ny_emojis.json"),
    EmojiKind.SLEEP: Path("/data/sleep_emojis.json"),
    EmojiKind.WALK: Path("/data/walking_emojis.json"),
}

def is_winter(today: date | None = None) -> bool:
    today = today or date.today()
    return today.month in (12, 1, 2)

def normalize_emoji_kind(kind: EmojiKind) -> EmojiKind:
    if kind == EmojiKind.DEFAULT and is_winter():
        return EmojiKind.NY
    return kind

def get_emoji_file_path(kind: EmojiKind) -> Path:
    kind = normalize_emoji_kind(kind)
    return EMOJI_FILES.get(kind, EMOJI_FILES[EmojiKind.DEFAULT])

def load_emojis(kind: EmojiKind = EmojiKind.DEFAULT):
    path = get_emoji_file_path(kind)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_emojis(emojis, kind: EmojiKind = EmojiKind.DEFAULT):
    path = get_emoji_file_path(kind)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(emojis, f, ensure_ascii=False, indent=2)

def get_random_emoji(kind: EmojiKind = EmojiKind.DEFAULT):
    emojis = load_emojis(kind)
    if not emojis:
        return TG_DEFAULT_EMOJI
    return int(random.choice(emojis))

def append_emoji(emoji: str, kind: EmojiKind = EmojiKind.DEFAULT):
    emojis = load_emojis(kind)
    emojis.append(emoji)
    save_emojis(emojis, kind)

def update_emoji(index: int, emoji: str, kind: EmojiKind = EmojiKind.DEFAULT):
    emojis = load_emojis(kind)
    if 0 <= index < len(emojis):
        emojis[index] = emoji
        save_emojis(emojis, kind)

def remove_emoji(index: int, kind: EmojiKind = EmojiKind.DEFAULT):
    emojis = load_emojis(kind)
    if 0 <= index < len(emojis):
        emojis.pop(index)
        save_emojis(emojis, kind)

def parse_emoji_kind(kind_str: str) -> EmojiKind:
    try:
        return EmojiKind(kind_str.lower())
    except ValueError:
        return EmojiKind.DEFAULT
