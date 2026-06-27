import aioredis
from typing import Literal
from models.redis import Player, Game
from services.redis import redis_client
from services.redis.game import game_key, getGame, saveGame

def player_key(code: str) -> str:
    return f"game:{code}:players"

async def savePlayer(code: str, player: Player):
    await redis_client.hset(player_key(code), player.id, player.model_dump_json())

async def checkPlayerExists(code: str, player_id: str):
    return await redis_client.hexists(player_key(code), player_id) == 1

async def addPlayer(code: str, player_id: str, role: Literal['host', 'player']) -> int:
    if not await checkPlayerExists(code, player_id):
        player = Player(
            id=player_id,
            username=None,
            score=0,
            role=role
        )
        await savePlayer(code, player)
        return 0
    else:
        return 21
    
async def removePlayer(code: str, player_id: str):
    await redis_client.hdel(player_key(code), player_id)

async def setPlayerUsername(code: str, player: Player, username: str):
    player.username = username
    await savePlayer(code, player)


