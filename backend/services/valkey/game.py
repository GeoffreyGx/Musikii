from typing import Literal
import time
from sqlalchemy.orm import Session
from glide import GlideClient, ExpirySet, ExpiryType
from models.valkey import Game, Round
from services.sql.library import getSongFromPlaylistIndex

GAME_TTL = 3600


def game_key(code: str) -> str:
    return f"game:{code}"

def round_key(code: str, index: int) -> str:
    return f"game:{code}:round:{index}"

async def checkGameExistence(client: GlideClient, code: str) -> bool:
    return await client.exists([game_key(code)]) == 1

async def newGame(client: GlideClient, code: str, host_id: str, playlist_id: str):
    game = Game(
        id=code,
        host_id=host_id,
        playlist_id=playlist_id,
        current_round_index=0,
        phase="LOBBY"
    )
    await saveGame(client, code, game)

async def saveGame(client: GlideClient, code: str, game: Game):
    await client.set(
        game_key(code),
        game.model_dump_json(),
        expiry=ExpirySet(ExpiryType.SEC, GAME_TTL),
    )

async def getGame(client: GlideClient, code: str) -> Game:
    raw = await client.get(game_key(code))
    if not raw:
        raise KeyError('Game not found')
    return Game.model_validate_json(raw)

async def closeGame(client: GlideClient, code: str):
    await client.delete([game_key(code)])

async def getRound(client: GlideClient, code: str, index: int):
    raw = await client.get(round_key(code, index))
    if not raw:
        raise KeyError('Round not found')
    return Round.model_validate_json(raw)

async def saveRound(client: GlideClient, code: str, round: Round):
    await client.set(
        round_key(code, round.index),
        round.model_dump_json(),
    )

async def nextRound(client: GlideClient, session: Session, code: str):
    game: Game = await getGame(client, code)
    if not game:
        raise KeyError('Game not found')
    
    next_song = getSongFromPlaylistIndex(session, game.playlist_id, game.current_round_index)
    if next_song == 22:
        raise KeyError("Song not found")
    new_round = Round(
        index=game.current_round_index + 1,
        song_id=next_song["id"],
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
    await saveRound(client, code, new_round)
    await saveGame(client, code, new_game)

async def isAnsweringWindowOpen(client: GlideClient, code: str):
    game: Game = await getGame(client, code)
    if not game:
        raise KeyError('Game not found')
    round: Round = await getRound(client, code, game.current_round_index)
    if not round:
        raise KeyError('Round not found')
    elapsed = time.time() - round.starting_time
    return elapsed <= round.round_duration

async def setGamePhase(client: GlideClient, code: str, phase: Literal["LOBBY", "COUNTDOWN", "PLAY", "ANSWER", "RESULTS"]):
    game: Game = await getGame(client, code)
    if not game:
        raise KeyError('Game not found')
    new_game = Game(
        id=game.id,
        host_id=game.host_id,
        playlist_id=game.playlist_id,
        current_round_index=game.current_round_index,
        phase=phase
    )
    await saveGame(client, code, new_game)