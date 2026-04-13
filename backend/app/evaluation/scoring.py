"""Heuristic auto-scoring for clone responses."""

from __future__ import annotations

import re
from statistics import mean

from app.models.persona import PersonaCore
from app.schemas.core import CloneRequest

AIISH_PHRASES = (
    "as an ai",
    "absolutely",
    "certainly",
    "i understand",
    "i apologize",
    "let me know if you need anything else",
    "i hope this helps",
)

EMOTIONAL_ISSUE_HINTS = ("emotion", "tone", "cold", "harsh", "aggressive", "flat")
HALLUCINATION_HINTS = ("halluc", "invent", "made up", "unsupported", "fact")
BOUNDARY_HINTS = ("policy", "boundary", "forbidden", "unsafe", "never say")


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: object, default: float = 0.5) -> float:
    try:
        return _clamp(float(value))
    except (TypeError, ValueError):
        return default


def _tokens(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def _jaccard_similarity(left: str, right: str) -> float:
    left_tokens = set(_tokens(left))
    right_tokens = set(_tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _length_similarity(left: str, right: str) -> float:
    left_count = max(len(_tokens(left)), 1)
    right_count = max(len(_tokens(right)), 1)
    return min(left_count, right_count) / max(left_count, right_count)


def _punctuation_similarity(left: str, right: str) -> float:
    marks = ("!", "?", ",", ".")
    left_len = max(len(left), 1)
    right_len = max(len(right), 1)
    similarities: list[float] = []
    for mark in marks:
        left_ratio = left.count(mark) / left_len
        right_ratio = right.count(mark) / right_len
        similarities.append(max(0.0, 1.0 - abs(left_ratio - right_ratio) * 20))
    return mean(similarities) if similarities else 0.0


def _length_score(text: str) -> float:
    token_count = len(_tokens(text))
    if 4 <= token_count <= 60:
        return 1.0
    if token_count < 4:
        return token_count / 4
    return max(0.25, 1 - ((token_count - 60) / 80))


def _issue_hit(issues: list[str], hints: tuple[str, ...]) -> bool:
    return any(any(hint in issue for hint in hints) for issue in issues)


def _ai_penalty(text: str) -> float:
    lowered = text.lower()
    hits = sum(1 for phrase in AIISH_PHRASES if phrase in lowered)
    hits += lowered.count("!!")
    return _clamp(hits / 4)


def build_auto_evaluation(
    *,
    persona: PersonaCore,
    request: CloneRequest,
    response_text: str,
    confidence: float,
    trace: dict | None,
    gold_answer: str | None,
) -> dict:
    trace = trace or {}
    critic_scores = trace.get("critic_scores", {}) if isinstance(trace, dict) else {}
    critic_issues = trace.get("critic_issues", []) if isinstance(trace, dict) else []
    issues = [str(issue).lower() for issue in critic_issues]

    style_score = _safe_float(critic_scores.get("style"))
    policy_score = _safe_float(critic_scores.get("policy"))
    authenticity_score = _safe_float(critic_scores.get("authenticity"))
    tone_score = _safe_float(critic_scores.get("tone"))
    confidence = _clamp(confidence)

    gold_similarity = 0.0
    if gold_answer:
        gold_similarity = (
            0.45 * _jaccard_similarity(response_text, gold_answer)
            + 0.3 * _length_similarity(response_text, gold_answer)
            + 0.25 * _punctuation_similarity(response_text, gold_answer)
        )

    length_score = _length_score(response_text)
    message_overlap = _jaccard_similarity(response_text, request.message)
    memories_count = int(trace.get("memories_count", 0)) if isinstance(trace, dict) else 0
    memory_signal = _clamp(memories_count / 4)
    never_say_hits = sum(
        1
        for phrase in persona.never_say or []
        if phrase and phrase.lower() in response_text.lower()
    )

    emotional_issue = _issue_hit(issues, EMOTIONAL_ISSUE_HINTS)
    hallucination_issue = _issue_hit(issues, HALLUCINATION_HINTS)
    boundary_issue = _issue_hit(issues, BOUNDARY_HINTS)
    ai_penalty = _ai_penalty(response_text)

    if gold_answer:
        style_similarity = _clamp(0.6 * style_score + 0.4 * gold_similarity)
        response_usefulness = _clamp(
            0.35 * gold_similarity
            + 0.3 * length_score
            + 0.2 * tone_score
            + 0.15 * confidence
        )
    else:
        style_similarity = _clamp(0.85 * style_score + 0.15 * length_score)
        response_usefulness = _clamp(
            0.45 * length_score
            + 0.25 * tone_score
            + 0.2 * authenticity_score
            + 0.1 * confidence
        )

    tone_fidelity = _clamp(0.75 * tone_score + 0.25 * (1.0 if not emotional_issue else 0.35))
    persona_consistency = _clamp(0.65 * authenticity_score + 0.35 * style_similarity)
    policy_compliance = _clamp(
        0.75 * policy_score
        + 0.25 * (1.0 if not boundary_issue and never_say_hits == 0 else 0.2)
    )
    memory_relevance = _clamp(
        0.45 * memory_signal
        + 0.35 * authenticity_score
        + 0.2 * max(message_overlap, 0.35)
    )
    hallucination_risk = _clamp(
        0.45 * (1 - authenticity_score)
        + 0.2 * (1 - confidence)
        + 0.2 * (1 - policy_compliance)
        + 0.15 * (1.0 if hallucination_issue else 0.0)
    )
    artificiality = _clamp(
        0.45 * (1 - authenticity_score)
        + 0.25 * (1 - style_similarity)
        + 0.2 * ai_penalty
        + 0.1 * (1 - length_score)
    )
    emotional_appropriateness = _clamp(
        0.7 * tone_fidelity + 0.3 * (1.0 if not emotional_issue else 0.35)
    )
    boundary_respect = _clamp(
        0.55 * policy_compliance + 0.45 * (1.0 if never_say_hits == 0 else 0.0)
    )

    overall_score = _clamp(
        mean(
            [
                style_similarity,
                tone_fidelity,
                persona_consistency,
                policy_compliance,
                memory_relevance,
                emotional_appropriateness,
                boundary_respect,
                response_usefulness,
                1 - hallucination_risk,
                1 - artificiality,
            ]
        )
    )

    if overall_score >= 0.78:
        verdict = "pass"
    elif overall_score >= 0.58:
        verdict = "mixed"
    else:
        verdict = "fail"

    notes: list[str] = []
    if gold_answer:
        notes.append("Auto-evaluated against the provided gold answer.")
    else:
        notes.append("Auto-evaluated from critic scores and response heuristics.")
    if critic_issues:
        notes.append("Critic issues: " + "; ".join(str(issue) for issue in critic_issues[:3]))

    thumbs: str | None = None
    if overall_score >= 0.72:
        thumbs = "up"
    elif overall_score < 0.5:
        thumbs = "down"

    return {
        "style_similarity": style_similarity,
        "tone_fidelity": tone_fidelity,
        "persona_consistency": persona_consistency,
        "policy_compliance": policy_compliance,
        "memory_relevance": memory_relevance,
        "hallucination_risk": hallucination_risk,
        "artificiality": artificiality,
        "emotional_appropriateness": emotional_appropriateness,
        "boundary_respect": boundary_respect,
        "response_usefulness": response_usefulness,
        "overall_score": overall_score,
        "verdict": verdict,
        "reviewer_notes": " ".join(notes),
        "thumbs": thumbs,
    }
