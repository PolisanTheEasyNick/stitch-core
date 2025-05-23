import json
import random
from pathlib import Path

from .config import TG_DEFAULT_STATUS

QUOTES_FILE = Path("/data/quotes.json")

def load_quotes():
    if not QUOTES_FILE.exists():
        return []
    with open(QUOTES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_quotes(quotes):
    with open(QUOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, indent=2)

def get_random_quote():
    quotes = load_quotes()
    if not quotes:
        return TG_DEFAULT_STATUS
    return random.choice(quotes)

def append_quote(quote: str):
    quotes = load_quotes()
    quotes.append(quote)
    save_quotes(quotes)

def remove_quote(index: int):
    quotes = load_quotes()
    if 0 <= index < len(quotes):
        quotes.pop(index)
        save_quotes(quotes)

def update_quote(index: int, quote: str):
    quotes = load_quotes()
    if 0 <= index < len(quotes):
        quotes[index] = quote
        save_quotes(quotes)
