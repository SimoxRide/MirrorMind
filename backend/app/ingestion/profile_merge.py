"""Helpers for merging chunked document extraction results and skipping duplicates."""

from __future__ import annotations

import copy
import re
from typing import Any


def normalize_dedupe_text(value: str | None) -> str:
    if not value:
        return ""
    collapsed = re.sub(r"\s+", " ", value).strip().lower()
    return collapsed


def merge_document_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    persona: dict[str, Any] = {}
    summaries: list[str] = []
    memories: list[dict[str, Any]] = []
    writing_samples: list[dict[str, Any]] = []
    policies: list[dict[str, Any]] = []
    traits: list[dict[str, Any]] = []

    for payload in payloads:
        persona = merge_persona_updates(persona, payload.get("persona") or {})
        summary = str(payload.get("summary") or "").strip()
        if summary and summary not in summaries:
            summaries.append(summary)
        memories.extend(payload.get("memories") or [])
        writing_samples.extend(payload.get("writing_samples") or [])
        policies.extend(payload.get("policies") or [])
        traits.extend(payload.get("traits") or [])

    deduped_memories, _ = dedupe_memory_items(memories)
    deduped_samples, _ = dedupe_writing_samples(writing_samples)
    deduped_policies, _ = dedupe_policy_items(policies)
    deduped_traits, _ = dedupe_trait_items(traits)

    return {
        "persona": persona or None,
        "summary": " ".join(summaries).strip(),
        "memories": deduped_memories,
        "writing_samples": deduped_samples,
        "policies": deduped_policies,
        "traits": deduped_traits,
    }


def merge_persona_updates(
    current: dict[str, Any] | None, incoming: dict[str, Any] | None
) -> dict[str, Any]:
    merged = copy.deepcopy(current or {})
    for key, value in (incoming or {}).items():
        if value is None:
            continue
        existing = merged.get(key)
        if isinstance(value, dict):
            merged[key] = merge_persona_updates(existing or {}, value)
        elif isinstance(value, list):
            merged[key] = _merge_unique_list((existing or []), value)
        elif isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                continue
            if not existing or len(candidate) > len(str(existing).strip()):
                merged[key] = candidate
        elif existing is None:
            merged[key] = value
    return merged


def dedupe_memory_items(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    merged: list[dict[str, Any]] = []
    title_index: dict[tuple[str, str], int] = {}
    content_index: dict[str, int] = {}
    duplicates = 0

    for item in items:
        normalized_title = normalize_dedupe_text(item.get("title"))
        normalized_content = normalize_dedupe_text(item.get("content"))
        memory_type = str(item.get("memory_type") or "")
        title_key = (memory_type, normalized_title) if normalized_title else None
        existing_index = None
        if title_key and title_key in title_index:
            existing_index = title_index[title_key]
        elif normalized_content and normalized_content in content_index:
            existing_index = content_index[normalized_content]

        if existing_index is None:
            merged_item = {
                "memory_type": memory_type or "long_term",
                "title": str(item.get("title") or "").strip(),
                "content": str(item.get("content") or "").strip(),
                "tags": _merge_unique_list([], item.get("tags") or []),
            }
            merged.append(merged_item)
            item_index = len(merged) - 1
            if title_key:
                title_index[title_key] = item_index
            if normalized_content:
                content_index[normalized_content] = item_index
            continue

        duplicates += 1
        merged[existing_index]["content"] = _prefer_longer(
            merged[existing_index].get("content"),
            item.get("content"),
        )
        merged[existing_index]["tags"] = _merge_unique_list(
            merged[existing_index].get("tags") or [],
            item.get("tags") or [],
        )

    return merged, duplicates


def dedupe_writing_samples(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    merged: list[dict[str, Any]] = []
    content_index: dict[str, int] = {}
    duplicates = 0

    for item in items:
        normalized_content = normalize_dedupe_text(item.get("content"))
        if not normalized_content:
            continue
        existing_index = content_index.get(normalized_content)
        if existing_index is None:
            merged.append(
                {
                    "content": str(item.get("content") or "").strip(),
                    "context_type": str(item.get("context_type") or "general"),
                    "tone": str(item.get("tone")).strip() if item.get("tone") else None,
                }
            )
            content_index[normalized_content] = len(merged) - 1
            continue

        duplicates += 1
        existing = merged[existing_index]
        if not existing.get("tone") and item.get("tone"):
            existing["tone"] = str(item.get("tone")).strip()
        if existing.get("context_type") == "general" and item.get("context_type"):
            existing["context_type"] = str(item.get("context_type"))

    return merged, duplicates


def dedupe_policy_items(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    merged: list[dict[str, Any]] = []
    name_index: dict[tuple[str, str], int] = {}
    description_index: dict[str, int] = {}
    duplicates = 0

    for item in items:
        policy_type = str(item.get("policy_type") or "tone")
        normalized_name = normalize_dedupe_text(item.get("name"))
        normalized_description = normalize_dedupe_text(item.get("description"))
        name_key = (policy_type, normalized_name) if normalized_name else None
        existing_index = None
        if name_key and name_key in name_index:
            existing_index = name_index[name_key]
        elif normalized_description and normalized_description in description_index:
            existing_index = description_index[normalized_description]

        if existing_index is None:
            merged.append(
                {
                    "policy_type": policy_type,
                    "name": str(item.get("name") or "").strip(),
                    "description": str(item.get("description") or "").strip(),
                }
            )
            item_index = len(merged) - 1
            if name_key:
                name_index[name_key] = item_index
            if normalized_description:
                description_index[normalized_description] = item_index
            continue

        duplicates += 1
        merged[existing_index]["description"] = _prefer_longer(
            merged[existing_index].get("description"),
            item.get("description"),
        )

    return merged, duplicates


def dedupe_trait_items(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    merged: list[dict[str, Any]] = []
    index: dict[tuple[str, str], int] = {}
    duplicates = 0

    for item in items:
        normalized_key = normalize_dedupe_text(item.get("key"))
        normalized_value = normalize_dedupe_text(item.get("value"))
        if not normalized_key or not normalized_value:
            continue
        pair = (normalized_key, normalized_value)
        existing_index = index.get(pair)
        confidence = float(item.get("confidence") or 0.0)

        if existing_index is None:
            merged.append(
                {
                    "key": str(item.get("key") or "").strip(),
                    "value": str(item.get("value") or "").strip(),
                    "confidence": max(0.0, min(1.0, confidence)),
                }
            )
            index[pair] = len(merged) - 1
            continue

        duplicates += 1
        merged[existing_index]["confidence"] = max(
            merged[existing_index].get("confidence") or 0.0,
            max(0.0, min(1.0, confidence)),
        )

    return merged, duplicates


def build_existing_import_index(
    memories: list[Any],
    writing_samples: list[Any],
    policies: list[Any],
) -> dict[str, set[Any]]:
    memory_titles: set[tuple[str, str]] = set()
    memory_contents: set[str] = set()
    sample_contents: set[str] = set()
    policy_names: set[tuple[str, str]] = set()
    policy_descriptions: set[str] = set()

    for item in memories:
        memory_type = str(_field(item, "memory_type") or "")
        title = normalize_dedupe_text(_field(item, "title"))
        content = normalize_dedupe_text(_field(item, "content"))
        if title:
            memory_titles.add((memory_type, title))
        if content:
            memory_contents.add(content)

    for item in writing_samples:
        content = normalize_dedupe_text(_field(item, "content"))
        if content:
            sample_contents.add(content)

    for item in policies:
        policy_type = str(_field(item, "policy_type") or "")
        name = normalize_dedupe_text(_field(item, "name"))
        description = normalize_dedupe_text(_field(item, "description"))
        if name:
            policy_names.add((policy_type, name))
        if description:
            policy_descriptions.add(description)

    return {
        "memory_titles": memory_titles,
        "memory_contents": memory_contents,
        "sample_contents": sample_contents,
        "policy_names": policy_names,
        "policy_descriptions": policy_descriptions,
    }


def estimate_import_counts(
    data: dict[str, Any],
    existing_index: dict[str, set[Any]],
) -> tuple[dict[str, int], dict[str, int]]:
    counts = {"memories": 0, "writing_samples": 0, "policies": 0}
    duplicates = {"memories": 0, "writing_samples": 0, "policies": 0}

    memory_titles = set(existing_index["memory_titles"])
    memory_contents = set(existing_index["memory_contents"])
    sample_contents = set(existing_index["sample_contents"])
    policy_names = set(existing_index["policy_names"])
    policy_descriptions = set(existing_index["policy_descriptions"])

    deduped_memories, _ = dedupe_memory_items(data.get("memories") or [])
    deduped_samples, _ = dedupe_writing_samples(data.get("writing_samples") or [])
    deduped_policies, _ = dedupe_policy_items(data.get("policies") or [])

    for item in deduped_memories:
        title_key = (
            str(item.get("memory_type") or ""),
            normalize_dedupe_text(item.get("title")),
        )
        content_key = normalize_dedupe_text(item.get("content"))
        if (title_key[1] and title_key in memory_titles) or (
            content_key and content_key in memory_contents
        ):
            duplicates["memories"] += 1
            continue
        counts["memories"] += 1
        if title_key[1]:
            memory_titles.add(title_key)
        if content_key:
            memory_contents.add(content_key)

    for item in deduped_samples:
        content_key = normalize_dedupe_text(item.get("content"))
        if content_key in sample_contents:
            duplicates["writing_samples"] += 1
            continue
        counts["writing_samples"] += 1
        sample_contents.add(content_key)

    for item in deduped_policies:
        name_key = (
            str(item.get("policy_type") or ""),
            normalize_dedupe_text(item.get("name")),
        )
        description_key = normalize_dedupe_text(item.get("description"))
        if (name_key[1] and name_key in policy_names) or (
            description_key and description_key in policy_descriptions
        ):
            duplicates["policies"] += 1
            continue
        counts["policies"] += 1
        if name_key[1]:
            policy_names.add(name_key)
        if description_key:
            policy_descriptions.add(description_key)

    return counts, duplicates


def _merge_unique_list(existing: list[Any], incoming: list[Any]) -> list[Any]:
    merged: list[Any] = []
    seen: set[str] = set()
    for item in [*existing, *incoming]:
        if item is None:
            continue
        marker = normalize_dedupe_text(str(item))
        if not marker or marker in seen:
            continue
        seen.add(marker)
        merged.append(item)
    return merged


def _prefer_longer(existing: Any, incoming: Any) -> str:
    existing_text = str(existing or "").strip()
    incoming_text = str(incoming or "").strip()
    if len(incoming_text) > len(existing_text):
        return incoming_text
    return existing_text


def _field(item: Any, name: str) -> Any:
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)
