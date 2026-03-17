import aioredis
from sqlalchemy.orm import Session
from models.redis import *
from services.sql import getSongFromPlaylistIndex

REDIS_URL = "redis://localhost:6379"
GAME_TTL = 3600

redis_client = aioredis.from_url(
    REDIS_URL,
    decode_response=True
)

def game_key(code: str) -> str:
    return f"game:{code}"

async def checkGameExistence(code: str) -> bool:
    return await redis_client.exists(game_key(code)) == 1

async def newGame(code: str, host_id: str, playlist_id: str):
    game = Game(
        id=code,
        host_id=host_id,
        playlist_id=playlist_id,
        players=[],
        current_round_index=0,
        phase="LOBBY"
    )
    await saveGame(code, game)

async def saveGame(code: str, game: Game):
    redis_client.set(
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

# async def gameNextSong(session: Session, code: str, ):
#     game: Game = await getGame(code)
#     if not game:
#         raise KeyError('Game not found')
#     nextSong = getSongFromPlaylistIndex(session, game.playlist_id, game.current_round_index)
#     if nextSong == 22:
#         raise KeyError("Song not found")
