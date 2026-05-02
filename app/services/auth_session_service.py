import json
from uuid import uuid4

from app.core.redis import redis_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_refresh_token_ttl_seconds,
    hash_refresh_token,
)


class AuthSessionService:
    PREFIX = "auth:refresh"

    @classmethod
    def _key(cls, session_id: str) -> str:
        return f"{cls.PREFIX}:{session_id}"

    @classmethod
    async def create_session(cls, user_id: str) -> dict:
        session_id = str(uuid4())
        refresh_token = create_refresh_token()
        refresh_token_hash = hash_refresh_token(refresh_token)
        ttl = get_refresh_token_ttl_seconds()

        payload = {
            "user_id": user_id,
            "token_hash": refresh_token_hash,
            "revoked": False,
        }

        await redis_client.set(
            cls._key(session_id),
            json.dumps(payload),
            ex=ttl,
        )

        access_token = create_access_token(
            user_id=user_id, session_id=session_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": session_id,
        }

    @classmethod
    async def refresh_session(cls, refresh_token: str) -> dict | None:
        refresh_hash = hash_refresh_token(refresh_token)

        async for key in redis_client.scan_iter(match=f"{cls.PREFIX}:*"):
            raw = await redis_client.get(key)
            if not raw:
                continue

            data = json.loads(raw)
            if data.get("revoked"):
                continue

            if data.get("token_hash") == refresh_hash:
                old_session_id = key.split(":")[-1]
                user_id = data["user_id"]

                await redis_client.delete(key)

                return await cls.create_session(user_id=user_id)

        return None

    @classmethod
    async def revoke_session_by_refresh_token(cls, refresh_token: str) -> bool:
        refresh_hash = hash_refresh_token(refresh_token)

        async for key in redis_client.scan_iter(match=f"{cls.PREFIX}:*"):
            raw = await redis_client.get(key)
            if not raw:
                continue

            data = json.loads(raw)
            if data.get("token_hash") == refresh_hash:
                await redis_client.delete(key)
                return True

        return False
