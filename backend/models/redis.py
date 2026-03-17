from pydantic import BaseModel
from typing import Literal

class Player(BaseModel):
    id: str
    username: str | None
    score: float
    role: Literal["host", "player"]

class Round(BaseModel):
    index: int
    song_id: str
    round_duration: int
    answers: dict[str, str]
    correct_players: list[str]

class Game(BaseModel):
    id: str
    host_id: str
    playlist_id: str
    players: list[str]
    current_round_index: int
    phase: Literal["LOBBY", "COUNTDOWN", "PLAY", "ANSWER", "RESULTS"]