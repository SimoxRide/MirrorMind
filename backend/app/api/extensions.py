"""Extensions API — manage third-party integrations (Telegram, Discord, WhatsApp)."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.extension import Extension
from app.models.user import User
from app.services.extension_service import ExtensionService
from app.workers import discord_bot, telegram_bot, whatsapp_bot

router = APIRouter(prefix="/extensions", tags=["Extensions"])


# ── Schemas ──────────────────────────────────────────────


class ExtensionCreate(BaseModel):
    persona_id: UUID
    platform: str
    label: str = ""
    credentials: dict | None = None
    config: dict | None = None


class ExtensionUpdate(BaseModel):
    label: str | None = None
    is_active: bool | None = None
    credentials: dict | None = None
    config: dict | None = None


class ExtensionRead(BaseModel):
    id: UUID
    persona_id: UUID
    platform: str
    label: str
    is_active: bool
    credentials: dict | None
    config: dict | None
    bot_running: bool = False
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ── Helpers ──────────────────────────────────────────────


def _svc(db: AsyncSession = Depends(get_db)) -> ExtensionService:
    return ExtensionService(db)


def _to_read(ext: Extension) -> ExtensionRead:
    creds = dict(ext.credentials) if ext.credentials else None
    if creds:
        # Mask sensitive tokens
        for key in ("bot_token", "access_token"):
            if key in creds:
                val = creds[key]
                creds[key] = val[:8] + "..." + val[-4:] if len(val) > 12 else "***"
    running = False
    if ext.platform == "telegram":
        running = telegram_bot.is_running(ext.id)
    elif ext.platform == "discord":
        running = discord_bot.is_running(ext.id)
    elif ext.platform == "whatsapp":
        running = ext.is_active  # webhook-based, always "running" when active
    return ExtensionRead(
        id=ext.id,
        persona_id=ext.persona_id,
        platform=ext.platform,
        label=ext.label,
        is_active=ext.is_active,
        credentials=creds,
        config=ext.config,
        bot_running=running,
        created_at=ext.created_at.isoformat(),
        updated_at=ext.updated_at.isoformat(),
    )


# ── Available platforms ──────────────────────────────────


PLATFORMS = [
    {
        "id": "telegram",
        "name": "Telegram",
        "description": "Connect your clone to a Telegram bot. Users can chat with your clone directly in Telegram.",
        "icon": "Send",
        "credential_fields": [
            {
                "key": "bot_token",
                "label": "Bot Token",
                "type": "password",
                "placeholder": "Paste your BotFather token...",
                "help": "Create a bot via @BotFather on Telegram and paste the token here.",
            },
        ],
    },
    {
        "id": "discord",
        "name": "Discord",
        "description": "Connect your clone to a Discord bot. Mention the bot or send a DM to chat.",
        "icon": "MessageCircle",
        "credential_fields": [
            {
                "key": "bot_token",
                "label": "Bot Token",
                "type": "password",
                "placeholder": "Paste your Discord bot token...",
                "help": "Create an application at discord.com/developers, add a Bot, enable MESSAGE CONTENT intent, and paste the token here.",
            },
        ],
    },
    {
        "id": "whatsapp",
        "name": "WhatsApp",
        "description": "Connect your clone to WhatsApp Business. Users can chat via WhatsApp.",
        "icon": "Phone",
        "credential_fields": [
            {
                "key": "access_token",
                "label": "Access Token",
                "type": "password",
                "placeholder": "Paste your permanent access token...",
                "help": "Use a System User token from Meta Business Suite for long-lived access.",
            },
            {
                "key": "phone_number_id",
                "label": "Phone Number ID",
                "type": "text",
                "placeholder": "e.g. 1234567890",
                "help": "Found in your WhatsApp Business App dashboard under Phone Numbers.",
            },
            {
                "key": "verify_token",
                "label": "Webhook Verify Token",
                "type": "text",
                "placeholder": "Choose a secret string...",
                "help": "A custom secret you'll enter in Meta's webhook configuration to verify the endpoint.",
            },
        ],
    },
]


@router.get("/platforms")
async def list_platforms(_user: User = Depends(get_current_user)):
    return PLATFORMS


# ── CRUD ─────────────────────────────────────────────────


@router.get("/", response_model=list[ExtensionRead])
async def list_extensions(
    persona_id: UUID,
    svc: ExtensionService = Depends(_svc),
    _user: User = Depends(get_current_user),
):
    exts = await svc.list_by_persona(persona_id)
    return [_to_read(e) for e in exts]


@router.post("/", response_model=ExtensionRead, status_code=201)
async def create_extension(
    data: ExtensionCreate,
    svc: ExtensionService = Depends(_svc),
    _user: User = Depends(get_current_user),
):
    ext = await svc.create(data.model_dump(exclude_none=True))
    return _to_read(ext)


@router.patch("/{ext_id}", response_model=ExtensionRead)
async def update_extension(
    ext_id: UUID,
    data: ExtensionUpdate,
    svc: ExtensionService = Depends(_svc),
    _user: User = Depends(get_current_user),
):
    ext = await svc.get(ext_id)
    if not ext:
        raise HTTPException(status_code=404, detail="Extension not found.")
    ext = await svc.update(ext, data.model_dump(exclude_unset=True))

    # Handle bot lifecycle
    await _sync_bot_lifecycle(ext)

    return _to_read(ext)


@router.delete("/{ext_id}", status_code=204)
async def delete_extension(
    ext_id: UUID,
    svc: ExtensionService = Depends(_svc),
    _user: User = Depends(get_current_user),
):
    ext = await svc.get(ext_id)
    if not ext:
        raise HTTPException(status_code=404, detail="Extension not found.")
    await _stop_platform_bot(ext)
    await svc.delete(ext)


# ── Toggle active ────────────────────────────────────────


@router.post("/{ext_id}/toggle", response_model=ExtensionRead)
async def toggle_extension(
    ext_id: UUID,
    svc: ExtensionService = Depends(_svc),
    _user: User = Depends(get_current_user),
):
    ext = await svc.get(ext_id)
    if not ext:
        raise HTTPException(status_code=404, detail="Extension not found.")

    new_active = not ext.is_active
    ext = await svc.update(ext, {"is_active": new_active})

    await _sync_bot_lifecycle(ext)

    return _to_read(ext)


# ── Bot lifecycle helpers ────────────────────────────────


async def _sync_bot_lifecycle(ext: Extension) -> None:
    """Start or stop a bot based on the extension's active state."""
    creds = ext.credentials or {}
    token = creds.get("bot_token") or creds.get("access_token")

    if ext.platform == "telegram":
        if ext.is_active and token:
            await telegram_bot.restart_bot(ext.id, token, ext.persona_id)
        else:
            await telegram_bot.stop_bot(ext.id)
    elif ext.platform == "discord":
        if ext.is_active and token:
            await discord_bot.restart_bot(ext.id, token, ext.persona_id)
        else:
            await discord_bot.stop_bot(ext.id)
    elif ext.platform == "whatsapp":
        if not ext.is_active:
            whatsapp_bot.clear_history(ext.id)


async def _stop_platform_bot(ext: Extension) -> None:
    """Stop all bot processes for an extension."""
    if ext.platform == "telegram":
        await telegram_bot.stop_bot(ext.id)
    elif ext.platform == "discord":
        await discord_bot.stop_bot(ext.id)
    elif ext.platform == "whatsapp":
        whatsapp_bot.clear_history(ext.id)


# ── WhatsApp Webhook ─────────────────────────────────────


@router.get("/webhooks/whatsapp/{ext_id}")
async def whatsapp_webhook_verify(
    ext_id: UUID,
    db: AsyncSession = Depends(get_db),
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta webhook verification endpoint."""
    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="Invalid mode.")

    svc = ExtensionService(db)
    ext = await svc.get(ext_id)
    if not ext or ext.platform != "whatsapp":
        raise HTTPException(status_code=404, detail="Extension not found.")

    verify_token = (ext.credentials or {}).get("verify_token", "")
    if hub_verify_token != verify_token:
        raise HTTPException(status_code=403, detail="Verify token mismatch.")

    return (
        int(hub_challenge)
        if hub_challenge and hub_challenge.isdigit()
        else hub_challenge
    )


@router.post("/webhooks/whatsapp/{ext_id}")
async def whatsapp_webhook_receive(
    ext_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive incoming WhatsApp messages via webhook."""
    svc = ExtensionService(db)
    ext = await svc.get(ext_id)
    if not ext or ext.platform != "whatsapp" or not ext.is_active:
        return {"status": "ignored"}

    body = await request.json()
    creds = ext.credentials or {}
    access_token = creds.get("access_token", "")
    phone_number_id = creds.get("phone_number_id", "")

    # Parse WhatsApp Cloud API webhook payload
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                if msg.get("type") != "text":
                    continue
                from_number = msg.get("from", "")
                text = msg.get("text", {}).get("body", "")
                if text and from_number:
                    # Process async to not block webhook response
                    asyncio.create_task(
                        whatsapp_bot.handle_incoming_message(
                            extension_id=ext.id,
                            persona_id=ext.persona_id,
                            access_token=access_token,
                            phone_number_id=phone_number_id,
                            from_number=from_number,
                            message_text=text,
                        )
                    )

    return {"status": "ok"}
