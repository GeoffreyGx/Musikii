import asyncio

from glide import GlideClient, GlideClientConfiguration, NodeAddress

addresses = [
    NodeAddress(host="localhost", port=6379)
]

client_config = GlideClientConfiguration(addresses)
_client: GlideClient | None = None
_client_lock = asyncio.Lock()


async def getValkeyClient() -> GlideClient:
    global _client

    if _client is None:
        async with _client_lock:
            if _client is None:
                _client = await GlideClient.create(client_config)
    return _client
