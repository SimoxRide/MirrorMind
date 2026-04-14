"""WhatsApp Cloud API worker — connects a production clone to WhatsApp.

Uses Meta's WhatsApp Cloud API which requires:
1. A Meta Business account
2. A WhatsApp Business App at https://developers.facebook.com
3. A phone number registered with WhatsApp Business API
4. A permanent access token (System User token recommended)
5. Webhook verification configured to point to this server

The webhook endpoint is registered in the extensions API router.
"""

import asyncio
from collections import defaultdict, deque
from uuid import UUID

import httpx

from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models.extension import Extension
from app.schemas.core import CloneRequest
from app.services.clone_engine import CloneEngine
from sqlalchemy import select

logger = get_logger("whatsapp_bot")

_MAX_HISTORY = 20

# In-memory conversation histories keyed by extension_id:phone_number
_chat_histories: dict[str, deque] = defaultdict(lambda: deque(maxlen=_MAX_HISTORY * 2))

WHATSAPP_API = "https://graph.facebook.com/v21.0/{phone_number_id}/messages"


async def send_message(
    access_token: str, phone_number_id: str, to: str, text: str
) -> None:
    """Send a text message via WhatsApp Cloud API."""
    async with httpx.AsyncClient(timeout=30) as http:
        await http.post(
            WHATSAPP_API.format(phone_number_id=phone_number_id),
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            },
        )


async def handle_incoming_message(
    extension_id: UUID,
    persona_id: UUID,
    access_token: str,
    phone_number_id: str,
    from_number: str,
    message_text: str,
) -> None:
    """Process an incoming WhatsApp message and reply with clone response."""
    history_key = f"{extension_id}:{from_number}"

    if message_text.strip().lower() in ("/reset", "reset", "/clear"):
        _chat_histories[history_key].clear()
        await send_message(
            access_token,
            phone_number_id,
            from_number,
            "Conversation cleared! Let's start fresh.",
        )
        return

    history = list(_chat_histories[history_key])

    try:
        async with async_session_factory() as db:
            async with db.begin():
                engine = CloneEngine(db)
                req = CloneRequest(
                    persona_id=persona_id,
                    message=message_text,
                    context_type="general",
                    conversation_history=history or None,
                )
                result = await engine.generate(req)
                reply = result.response
    except Exception as exc:
        logger.error("whatsapp_generate_error", error=str(exc))
        reply = "Sorry, something went wrong. Please try again."

    _chat_histories[history_key].append({"role": "user", "content": message_text})
    _chat_histories[history_key].append({"role": "assistant", "content": reply})

    await send_message(access_token, phone_number_id, from_number, reply)


def clear_history(extension_id: UUID) -> None:
    """Clear all conversation histories for an extension."""
    prefix = f"{extension_id}:"
    keys_to_remove = [k for k in _chat_histories if k.startswith(prefix)]
    for k in keys_to_remove:
        del _chat_histories[k]
