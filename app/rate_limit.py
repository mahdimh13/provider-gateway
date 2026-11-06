from fastapi import HTTPException
from redis.asyncio import Redis
from .config import settings

# Atomic fixed-window counter. One Redis operation prevents races between API replicas.
LUA = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return n
"""
async def enforce_rate_limit(redis: Redis, identity: str = 'global'):
    key = f'gateway:rate:{identity}'
    count = int(await redis.eval(LUA, 1, key, settings.service_rate_window_seconds))
    if count > settings.service_rate_limit:
        raise HTTPException(status_code=429, detail='Service rate limit exceeded', headers={'Retry-After': str(settings.service_rate_window_seconds)})
