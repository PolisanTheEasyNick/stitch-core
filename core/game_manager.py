import json
import os
from typing import List

from .config import TG_DEFAULT_GAME_EMOJI, PILED_DEFAULT_COLOR

GAMES_PATH = "/data/games.json"

def ensure_data_file():
    if not os.path.exists(GAMES_PATH):
        os.makedirs(os.path.dirname(GAMES_PATH), exist_ok=True)
        with open(GAMES_PATH, "w") as f:
            json.dump([], f)

def load_games() -> List[dict]:
    ensure_data_file()
    with open(GAMES_PATH, "r") as f:
        return json.load(f)

def save_games(games: List[dict]) -> None:
    with open(GAMES_PATH, "w") as f:
        json.dump(games, f, indent=2)

def append_game(game: dict) -> None:
    games = load_games()
    games.append(game)
    save_games(games)

def update_game(index: int, game: dict) -> None:
    games = load_games()
    if index < 0 or index >= len(games):
        raise IndexError("Game index out of range")
    games[index] = game
    save_games(games)

def remove_game(index: int) -> None:
    games = load_games()
    if index < 0 or index >= len(games):
        raise IndexError("Game index out of range")
    games.pop(index)
    save_games(games)

def find_game_by_query(query: str) -> dict | None:
    games = load_games()

    for game in games:
        if game.get("steam_id") == query or game.get("name") == query:
            return game

    for game in games:
        if game.get("name") == "default game icon":
            return game

    return {
        "game": "Default",
        "color": PILED_DEFAULT_COLOR,
        "emoji": TG_DEFAULT_GAME_EMOJI
    }