from fastapi import FastAPI, HTTPException, Response, Request
import asyncpg
import redis.asyncio as redis
import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

# =========================
# App & Config
# =========================

app = FastAPI()

DB_URL = os.environ["DATABASE_URL"]
REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])

MAGIC_TTL = timedelta(minutes=5)
SESSION_TTL_SECONDS = 24 * 60 * 60

pg: asyncpg.Pool | None = None
rds: redis.Redis | None = None

# =========================
# Helpers
# =========================

def now() -> datetime:
    return datetime.now(timezone.utc)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# =========================
# Startup
# =========================

@app.on_event("startup")
async def startup():
    global pg, rds

    pg = await asyncpg.create_pool(dsn=DB_URL)
    rds = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
    )

    async with pg.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS magic_tokens (
            token_hash TEXT PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id),
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        );
        """)

# =========================
# Request Magic Link
# =========================

@app.post("/auth/magic/request")
async def request_magic_link(payload: dict):
    email = payload.get("email")
    print(email)
    if not email:
        return {"ok": True}

    async with pg.acquire() as conn:
        user = await conn.fetchrow(
            """
            INSERT INTO users(email)
            VALUES($1)
            ON CONFLICT(email)
            DO UPDATE SET email = EXCLUDED.email
            RETURNING id
            """,
            email.lower(),
        )

        token = secrets.token_hex(32)
        token_hash = hash_token(token)

        await conn.execute(
            """
            INSERT INTO magic_tokens(token_hash, user_id, expires_at)
            VALUES($1, $2, $3)
            """,
            token_hash,
            user["id"],
            now() + MAGIC_TTL,
        )

    # Simulated email
    print(
        f"Magic link → http://localhost:8000/auth/magic/consume?token={token}"
    )

    return {"ok": True}

# =========================
# Consume Magic Link
# =========================

@app.get("/auth/magic/consume")
async def consume_magic(token: str, response: Response):
    token_hash = hash_token(token)

    async with pg.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT user_id, expires_at, used_at
                FROM magic_tokens
                WHERE token_hash = $1
                FOR UPDATE
                """,
                token_hash,
            )

            if not row:
                raise HTTPException(401, "Invalid token")

            if row["used_at"] is not None:
                raise HTTPException(401, "Token already used")

            if row["expires_at"] < now():
                raise HTTPException(401, "Token expired")

            await conn.execute(
                "UPDATE magic_tokens SET used_at = now() WHERE token_hash = $1",
                token_hash,
            )

    # Create session
    session_id = secrets.token_hex(32)
    user_id = row["user_id"]

    old_session = await rds.get(f"user_sess:{user_id}")
    if old_session:
        await rds.delete(f"sess:{old_session}")

    await rds.setex(
        f"sess:{session_id}",
        SESSION_TTL_SECONDS,
        str(user_id),
    )
    await rds.setex(
        f"user_sess:{user_id}",
        SESSION_TTL_SECONDS,
        session_id,
    )

    response.set_cookie(
        key="sid",
        value=session_id,
        httponly=True,
        secure=False,      # set True in HTTPS
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
    )

    return {"ok": True}

# =========================
# Auth Middleware
# =========================

async def require_auth(request: Request):
    sid = request.cookies.get("sid")
    if not sid:
        raise HTTPException(401, "Not authenticated")

    user_id = await rds.get(f"sess:{sid}")
    if not user_id:
        raise HTTPException(401, "Session expired")

    request.state.user_id = int(user_id)

# =========================
# Protected Endpoint
# =========================

@app.get("/me")
async def me(request: Request):
    await require_auth(request)
    return {"user_id": request.state.user_id}
