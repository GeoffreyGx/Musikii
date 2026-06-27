from typing import Literal
import aioredis
import time
from sqlalchemy.orm import Session
from models.redis import *
from services.sql.library import getSongFromPlaylistIndex

REDIS_URL = "redis://localhost:6379"
GAME_TTL = 3600

redis_client = aioredis.from_url(
    REDIS_URL,
    decode_response=True
)

def game_key(code: str) -> str:
    return f"game:{code}"

def round_key(code: str, index: int) -> str:
    return f"game:{code}:round:{index}"

async def checkGameExistence(code: str) -> bool:
    return await redis_client.exists(game_key(code)) == 1

async def newGame(code: str, host_id: str, playlist_id: str):
    game = Game(
        id=code,
        host_id=host_id,
        playlist_id=playlist_id,
        current_round_index=0,
        phase="LOBBY"
    )
    await saveGame(code, game)

async def saveGame(code: str, game: Game):
    await redis_client.set(
        game_key(code),
        game.model_dump_json(),
        ex=GAME_TTL
    )

async def getGame(code: str) -> Game:
    raw = await redis_client.get(game_key(code))
    if not raw:
        raise KeyError('Game not found')
    return Game.model_validate_json(str(raw))

async def closeGame(code: str):
    await redis_client.delete(game_key(code))

async def getRound(code: str, index: int):
    raw = await redis_client.get(round_key(code, index))
    if not raw:
        raise KeyError('Round not found')
    return Round.model_validate_json(str(raw))

async def saveRound(code: str, round: Round):
    await redis_client.set(
        round_key(code, round.index),
        round.model_dump_json(),
    )

async def nextRound(session: Session, code: str):
    game: Game = await getGame(code)
    if not game:
        raise KeyError('Game not found')
    
    nextSong = getSongFromPlaylistIndex(session, game.playlist_id, game.current_round_index)
    if nextSong == 22:
        raise KeyError("Song not found")
    new_round = Round(
        index=game.current_round_index + 1,
        song_id=nextSong["id"],
        starting_time=time.time(),
        round_duration=30,
        answers={},
        correct_players=[]
    )
    new_game = Game(
        id=game.id,
        host_id=game.host_id,
        playlist_id=game.playlist_id,
        current_round_index=game.current_round_index + 1,
        phase="COUNTDOWN"
    )
    await saveRound(code, new_round)
    await saveGame(code, new_game)

async def isAnsweringWindowOpen(code: str):
    game: Game = await getGame(code)
    if not game:
        raise KeyError('Game not found')
    round: Round = await getRound(code, game.current_round_index)
    if not round:
        raise KeyError('Round not found')
    elapsed = time.time() - round.starting_time
    return elapsed <= round.round_duration

async def setGamePhase(code: str, phase: Literal["LOBBY", "COUNTDOWN", "PLAY", "ANSWER", "RESULTS"]):
    game: Game = await getGame(code)
    if not game:
        raise KeyError('Game not found')
    new_game = Game(
        id=game.id,
        host_id=game.host_id,
        playlist_id=game.playlist_id,
        current_round_index=game.current_round_index,
        phase=phase
    )
    await saveGame(code, new_game)