"""Discord bot worker — connects a production clone to a Discord bot.

Uses Discord Gateway (WebSocket) so no public URL is needed.
Each active Discord extension runs as an asyncio background task.

The user needs to:
1. Create a Discord Application at https://discord.com/developers
2. Create a Bot and copy the token
3. Enable MESSAGE CONTENT intent in the Bot settings
4. Invite the bot to a server with the OAuth2 URL generator (bot scope + Send Messages permission)
"""

import asyncio
import json
from collections import defaultdict, deque
from uuid import UUID

import httpx

from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models.extension import Extension
from app.schemas.core import CloneRequest
from app.services.clone_engine import CloneEngine
from sqlalchemy import select

logger = get_logger("discord_bot")

_active_bots: dict[str, asyncio.Task] = {}
_MAX_HISTORY = 20

DISCORD_API = "https://discord.com/api/v10"
DISCORD_GATEWAY = "wss://gateway.discord.gg/?v=10&encoding=json"


async def _send_message(
    http: httpx.AsyncClient, token: str, channel_id: str, content: str
) -> None:
    """Send a message to a Discord channel."""
    # Discord has a 2000 char limit per message
    for i in range(0, len(content), 2000):
        await http.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {token}"},
            json={"content": content[i : i + 2000]},
        )


async def _gateway_loop(extension_id: UUID, token: str, persona_id: UUID) -> None:
    """Discord Gateway WebSocket loop."""
    import websockets

    chat_histories: dict[str, deque] = defaultdict(
        lambda: deque(maxlen=_MAX_HISTORY * 2)
    )
    heartbeat_interval = 41250  # ms, will be updated from HELLO
    sequence = None
    session_id = None
    resume_gateway_url = None

    async with httpx.AsyncClient(timeout=30) as http:
        # Get bot user id
        me_resp = await http.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bot {token}"},
        )
        if me_resp.status_code != 200:
            logger.error("discord_auth_failed", status=me_resp.status_code)
            return
        bot_user_id = me_resp.json()["id"]

        while True:
            try:
                gateway_url = resume_gateway_url or DISCORD_GATEWAY
                async with websockets.connect(gateway_url) as ws:
                    # Receive HELLO
                    hello = json.loads(await ws.recv())
                    if hello.get("op") == 10:
                        heartbeat_interval = hello["d"]["heartbeat_interval"]

                    # If we have a session, try to resume
                    if session_id and sequence is not None:
                        await ws.send(
                            json.dumps(
                                {
                                    "op": 6,
                                    "d": {
                                        "token": token,
                                        "session_id": session_id,
                                        "seq": sequence,
                                    },
                                }
                            )
                        )
                    else:
                        # IDENTIFY
                        await ws.send(
                            json.dumps(
                                {
                                    "op": 2,
                                    "d": {
                                        "token": token,
                                        "intents": 512
                                        | 32768,  # GUILDS | MESSAGE_CONTENT
                                        "properties": {
                                            "os": "linux",
                                            "browser": "mirrormind",
                                            "device": "mirrormind",
                                        },
                                    },
                                }
                            )
                        )

                    # Start heartbeat task
                    async def heartbeat():
                        while True:
                            await asyncio.sleep(heartbeat_interval / 1000)
                            await ws.send(json.dumps({"op": 1, "d": sequence}))

                    hb_task = asyncio.create_task(heartbeat())

                    try:
                        async for raw_msg in ws:
                            payload = json.loads(raw_msg)
                            op = payload.get("op")
                            t = payload.get("t")
                            d = payload.get("d")

                            if payload.get("s"):
                                sequence = payload["s"]

                            # Reconnect requested
                            if op == 7:
                                break

                            # Invalid session
                            if op == 9:
                                session_id = None
                                sequence = None
                                await asyncio.sleep(5)
                                break

                            # READY — store session info
                            if t == "READY" and d:
                                session_id = d.get("session_id")
                                resume_gateway_url = d.get("resume_gateway_url")
                                logger.info(
                                    "discord_bot_ready", extension_id=str(extension_id)
                                )

                            # MESSAGE_CREATE
                            if t == "MESSAGE_CREATE" and d:
                                # Ignore own messages and other bots
                                author = d.get("author", {})
                                if author.get("id") == bot_user_id or author.get("bot"):
                                    continue

                                content = d.get("content", "").strip()
                                channel_id = d.get("channel_id")
                                if not content or not channel_id:
                                    continue

                                # Check if bot is mentioned or in DM
                                is_dm = d.get("guild_id") is None
                                mentions = [m.get("id") for m in d.get("mentions", [])]
                                is_mentioned = bot_user_id in mentions

                                if not is_dm and not is_mentioned:
                                    continue

                                # Strip bot mention from message
                                clean_content = content.replace(
                                    f"<@{bot_user_id}>", ""
                                ).strip()
                                if not clean_content:
                                    clean_content = "Hello"

                                # Use channel_id as conversation key
                                history_key = channel_id
                                history = list(chat_histories[history_key])

                                if clean_content.lower() in ("!reset", "!clear"):
                                    chat_histories[history_key].clear()
                                    await _send_message(
                                        http,
                                        token,
                                        channel_id,
                                        "Conversation cleared! Let's start fresh.",
                                    )
                                    continue

                                # Show typing indicator
                                await http.post(
                                    f"{DISCORD_API}/channels/{channel_id}/typing",
                                    headers={"Authorization": f"Bot {token}"},
                                )

                                # Generate clone response
                                try:
                                    async with async_session_factory() as db:
                                        async with db.begin():
                                            engine = CloneEngine(db)
                                            req = CloneRequest(
                                                persona_id=persona_id,
                                                message=clean_content,
                                                context_type="general",
                                                conversation_history=history or None,
                                            )
                                            result = await engine.generate(req)
                                            reply = result.response
                                except Exception as exc:
                                    logger.error(
                                        "discord_generate_error", error=str(exc)
                                    )
                                    reply = (
                                        "Sorry, something went wrong. Please try again."
                                    )

                                chat_histories[history_key].append(
                                    {"role": "user", "content": clean_content}
                                )
                                chat_histories[history_key].append(
                                    {"role": "assistant", "content": reply}
                                )

                                await _send_message(http, token, channel_id, reply)

                    finally:
                        hb_task.cancel()
                        try:
                            await hb_task
                        except asyncio.CancelledError:
                            pass

            except asyncio.CancelledError:
                logger.info("discord_bot_stopped", extension_id=str(extension_id))
                return
            except Exception as exc:
                logger.error("discord_gateway_error", error=str(exc))
                await asyncio.sleep(5)


async def start_bot(extension_id: UUID, token: str, persona_id: UUID) -> None:
    key = str(extension_id)
    if key in _active_bots and not _active_bots[key].done():
        return
    task = asyncio.create_task(
        _gateway_loop(extension_id, token, persona_id),
        name=f"discord-{key}",
    )
    _active_bots[key] = task
    logger.info("discord_bot_started", extension_id=key)


async def stop_bot(extension_id: UUID) -> None:
    key = str(extension_id)
    task = _active_bots.pop(key, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("discord_bot_stopped", extension_id=key)


async def restart_bot(extension_id: UUID, token: str, persona_id: UUID) -> None:
    await stop_bot(extension_id)
    await start_bot(extension_id, token, persona_id)


def is_running(extension_id: UUID) -> bool:
    key = str(extension_id)
    task = _active_bots.get(key)
    return task is not None and not task.done()


async def resume_all_bots() -> None:
    async with async_session_factory() as db:
        result = await db.execute(
            select(Extension).where(
                Extension.platform == "discord",
                Extension.is_active == True,  # noqa: E712
            )
        )
        for ext in result.scalars().all():
            token = (ext.credentials or {}).get("bot_token")
            if token:
                await start_bot(ext.id, token, ext.persona_id)


async def stop_all_bots() -> None:
    for key in list(_active_bots):
        task = _active_bots.pop(key)
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
