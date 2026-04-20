"""Telegram bot worker — connects a production clone to a Telegram bot.

Uses long-polling (getUpdates) so no public webhook URL is needed.
Each active Telegram extension runs as an asyncio background task.
"""

import asyncio
from collections import defaultdict, deque
from uuid import UUID

import httpx

from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models.extension import Extension
from app.models.production import ProductionClone
from app.schemas.core import CloneRequest
from app.services.clone_engine import CloneEngine
from sqlalchemy import select

logger = get_logger("telegram_bot")

# Active bot tasks keyed by extension id
_active_bots: dict[str, asyncio.Task] = {}

TELEGRAM_API = "https://api.telegram.org/bot{token}"

# Max conversation turns to keep per chat (user + assistant = 1 turn)
_MAX_HISTORY = 20


async def _poll_loop(extension_id: UUID, token: str, persona_id: UUID) -> None:
    """Long-polling loop that forwards Telegram messages to the clone engine."""
    base_url = TELEGRAM_API.format(token=token)
    offset = 0
    backoff = 5  # exponential backoff starting value
    # Per-chat conversation history: chat_id -> deque of {role, content}
    chat_histories: dict[int, deque] = defaultdict(
        lambda: deque(maxlen=_MAX_HISTORY * 2)
    )

    async with httpx.AsyncClient(timeout=30) as http:
        while True:
            try:
                resp = await http.get(
                    f"{base_url}/getUpdates",
                    params={"offset": offset, "timeout": 20},
                )
                data = resp.json()
                if not data.get("ok"):
                    logger.warning("telegram_poll_error", detail=data)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                    continue

                backoff = 5  # reset on success

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    message = update.get("message")
                    if not message or not message.get("text"):
                        continue

                    chat_id = message["chat"]["id"]
                    text = message["text"]

                    if text.startswith("/start"):
                        chat_histories[chat_id].clear()
                        await http.post(
                            f"{base_url}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": "Hello! I'm your MirrorMind clone. Send me a message and I'll reply in character.",
                            },
                        )
                        continue

                    if text.startswith("/reset"):
                        chat_histories[chat_id].clear()
                        await http.post(
                            f"{base_url}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": "Conversation history cleared. Let's start fresh!",
                            },
                        )
                        continue

                    # Build conversation history for the clone engine
                    history = list(chat_histories[chat_id])

                    # Generate clone response
                    try:
                        async with async_session_factory() as db:
                            async with db.begin():
                                engine = CloneEngine(db)
                                req = CloneRequest(
                                    persona_id=persona_id,
                                    message=text,
                                    context_type="general",
                                    conversation_history=history or None,
                                )
                                result = await engine.generate(req)
                                reply = result.response
                    except Exception as exc:
                        logger.error("telegram_generate_error", error=str(exc))
                        reply = "Sorry, something went wrong. Please try again."

                    # Store the turn in history
                    chat_histories[chat_id].append({"role": "user", "content": text})
                    chat_histories[chat_id].append(
                        {"role": "assistant", "content": reply}
                    )

                    await http.post(
                        f"{base_url}/sendMessage",
                        json={"chat_id": chat_id, "text": reply},
                    )

            except asyncio.CancelledError:
                logger.info("telegram_bot_stopped", extension_id=str(extension_id))
                return
            except Exception as exc:
                logger.error("telegram_poll_exception", error=str(exc))
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)


async def start_bot(extension_id: UUID, token: str, persona_id: UUID) -> None:
    """Start a Telegram bot background task for the given extension."""
    key = str(extension_id)
    if key in _active_bots and not _active_bots[key].done():
        return  # already running

    task = asyncio.create_task(
        _poll_loop(extension_id, token, persona_id),
        name=f"telegram-{key}",
    )
    _active_bots[key] = task
    logger.info("telegram_bot_started", extension_id=key)


async def stop_bot(extension_id: UUID) -> None:
    """Stop a running Telegram bot task."""
    key = str(extension_id)
    task = _active_bots.pop(key, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("telegram_bot_stopped", extension_id=key)


async def restart_bot(extension_id: UUID, token: str, persona_id: UUID) -> None:
    """Restart a bot (stop then start)."""
    await stop_bot(extension_id)
    await start_bot(extension_id, token, persona_id)


def is_running(extension_id: UUID) -> bool:
    key = str(extension_id)
    task = _active_bots.get(key)
    return task is not None and not task.done()


async def resume_all_bots() -> None:
    """Called on app startup to resume all active Telegram extensions."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Extension).where(
                Extension.platform == "telegram",
                Extension.is_active == True,  # noqa: E712
            )
        )
        extensions = result.scalars().all()
        for ext in extensions:
            token = (ext.credentials or {}).get("bot_token")
            if token:
                await start_bot(ext.id, token, ext.persona_id)
        if extensions:
            logger.info("telegram_bots_resumed", count=len(extensions))


async def stop_all_bots() -> None:
    """Called on app shutdown."""
    for key in list(_active_bots):
        task = _active_bots.pop(key)
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    logger.info("telegram_all_bots_stopped")
