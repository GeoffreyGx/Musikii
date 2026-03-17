import aioredis

def player_key(code: str) -> str:
    return f"game:{code}:players"

