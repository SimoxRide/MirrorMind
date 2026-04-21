"""Vision analysis for memory images.

Uses an OpenAI v1-compatible multimodal chat model (e.g. gpt-4o) to extract
structured details from an uploaded image. The caller provides the raw bytes
and the ``kind`` of image; we return a JSON-ish dict ready to be stored in
``MemoryImage.analysis``.

Failure-mode: when no provider API key is configured we degrade gracefully,
returning a ``skipped`` result instead of raising so manual uploads still work.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from openai import AsyncOpenAI

from app.core.logging import get_logger
from app.models.user import User
from app.services.provider_settings import resolve_provider_settings

logger = get_logger("image_analysis")


_SYSTEM_PROMPTS: dict[str, str] = {
    "self": (
        "You are analysing a SELF portrait of a person for whom we are building "
        "a high-fidelity virtual clone. Extract only information that is "
        "visually evident. Never invent identity, name or private data. "
        "Return a JSON object with keys: "
        "appearance (short description of hair, eyes, skin, build, distinctive "
        "features, estimated age range), "
        "style (clothing, accessories, colour palette, overall aesthetic), "
        "mood (expression, vibe conveyed by the photo), "
        "setting (where the photo seems taken), "
        "persona_hints (list of short, first-person style traits the clone "
        "could adopt, e.g. 'casual and approachable tone', 'loves outdoor "
        "activities based on gear visible'), "
        "identity_summary_addendum (a 1-2 sentence third-person paragraph "
        "that could be appended to the persona identity summary)."
    ),
    "person": (
        "You are analysing a photo of a person who is part of the life of the "
        "subject we are cloning. Extract only what is visually evident. "
        "Return a JSON object with keys: "
        "appearance, apparent_age_range, mood, setting, relationship_hints "
        "(list of short guesses about who they might be — family, friend, "
        "colleague — based on context ONLY if obvious, otherwise empty), "
        "description (2-3 sentence neutral caption)."
    ),
    "memory": (
        "You are analysing a personal memory photo belonging to the subject we "
        "are cloning. Extract only visual facts. "
        "Return a JSON object with keys: "
        "scene (what is happening), "
        "location_hints (any geography, landmark or indoor/outdoor cue), "
        "people_count (integer), "
        "mood (emotional tone of the scene), "
        "objects (notable objects), "
        "time_hints (indoor lighting, season, day/night, approximate era if "
        "clothes/tech suggest it), "
        "description (2-3 sentence neutral caption suitable to use as the "
        "memory content), "
        "suggested_tags (list of 3-8 short tags)."
    ),
}


async def analyze_image(
    image_bytes: bytes,
    content_type: str,
    kind: str,
    *,
    user: User | None,
    extra_context: str | None = None,
) -> dict[str, Any]:
    """Run vision analysis on ``image_bytes`` and return a dict.

    Returns ``{"status": "skipped", ...}`` when no API key is configured or the
    model is not multimodal.  Returns ``{"status": "failed", ...}`` on any
    other error.  On success returns ``{"status": "ready", "result": {...},
    "model": "..."}``.
    """
    provider = resolve_provider_settings(user)
    if not provider.configured:
        return {"status": "skipped", "reason": "no_api_key"}

    system_prompt = _SYSTEM_PROMPTS.get(kind, _SYSTEM_PROMPTS["memory"])
    if extra_context:
        system_prompt = f"{system_prompt}\n\nAdditional context: {extra_context}"

    mime = content_type or "image/jpeg"
    data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"

    client_kwargs: dict[str, Any] = {"api_key": provider.api_key}
    if provider.api_base:
        client_kwargs["base_url"] = provider.api_base
    client = AsyncOpenAI(**client_kwargs)

    try:
        completion = await client.chat.completions.create(
            model=provider.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Analyse this image and respond ONLY with a "
                                "valid JSON object — no prose, no markdown."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
    except Exception as exc:  # noqa: BLE001 — broad to never leak
        logger.warning("image_analysis_failed", error=str(exc), kind=kind)
        return {"status": "failed", "reason": str(exc)[:500]}

    raw = (completion.choices[0].message.content or "").strip()
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = {"raw": raw}

    return {
        "status": "ready",
        "model": provider.model,
        "kind": kind,
        "result": parsed,
    }
