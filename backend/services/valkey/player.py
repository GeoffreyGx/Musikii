from typing import Literal
from glide import GlideClient
from models.valkey import Player
from services.valkey.game import game_key, getGame, saveGame

def player_key(code: str) -> str:
    return f"game:{code}:players"

async def savePlayer(client: GlideClient, code: str, player: Player):
    await client.hset(player_key(code), {player.id: player.model_dump_json()})

async def checkPlayerExists(client: GlideClient, code: str, player_id: str):
    return await client.hexists(player_key(code), player_id) == 1

async def addPlayer(client: GlideClient, code: str, player_id: str, role: Literal['host', 'player']) -> int:
    if not await checkPlayerExists(client, code, player_id):
        player = Player(
            id=player_id,
            username=None,
            score=0,
            role=role
        )
        await savePlayer(client, code, player)
        return 0
    else:
        return 21
    
async def removePlayer(client: GlideClient, code: str, player_id: str):
   await client.hdel(player_key(code), [player_id])

async def setPlayerUsername(client: GlideClient, code: str, player: Player, username: str):
    player.username = username
    await savePlayer(client, code, player)


