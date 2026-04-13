"""Heuristic auto-scoring for clone responses.

When a gold answer is provided the evaluator performs deep analysis of:
- Grammar & punctuation patterns (emoji, abbreviations, capitalization)
- Writing style (sentence length, vocabulary, formality)
- Response length (strict matching against gold)
- Content accuracy (n-gram overlap, keyword coverage)
- Tone & emotional register

When the evaluation is negative it produces structured *improvement_suggestions*
that the frontend can present to the user for one-click application.
"""

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
    "happy to help",
    "of course",
    "great question",
)

EMOTIONAL_ISSUE_HINTS = ("emotion", "tone", "cold", "harsh", "aggressive", "flat")
HALLUCINATION_HINTS = ("halluc", "invent", "made up", "unsupported", "fact")
BOUNDARY_HINTS = ("policy", "boundary", "forbidden", "unsafe", "never say")

# ── Helpers ──────────────────────────────────────────────


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: object, default: float = 0.5) -> float:
    try:
        return _clamp(float(value))
    except (TypeError, ValueError):
        return default


def _tokens(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def _sentences(text: str) -> list[str]:
    """Split into sentences (handles ?, !, . and newlines)."""
    parts = re.split(r"[.!?]+|\n+", text)
    return [s.strip() for s in parts if s.strip()]


def _ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


# ── Similarity functions ─────────────────────────────────


def _jaccard_similarity(left: str, right: str) -> float:
    left_tokens = set(_tokens(left))
    right_tokens = set(_tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _ngram_overlap(left: str, right: str, n: int = 2) -> float:
    """Compute n-gram overlap (bigram by default) for deeper content matching."""
    lt = _tokens(left)
    rt = _tokens(right)
    left_ng = set(_ngrams(lt, n))
    right_ng = set(_ngrams(rt, n))
    if not left_ng or not right_ng:
        return 0.0
    return len(left_ng & right_ng) / len(left_ng | right_ng)


def _content_coverage(gold: str, response: str) -> float:
    """How many gold keywords appear in the response (directional recall)."""
    gold_tokens = set(_tokens(gold))
    resp_tokens = set(_tokens(response))
    if not gold_tokens:
        return 1.0
    # Filter out very short / stop-like words
    gold_meaningful = {t for t in gold_tokens if len(t) > 2}
    if not gold_meaningful:
        return 1.0
    return len(gold_meaningful & resp_tokens) / len(gold_meaningful)


def _length_similarity(left: str, right: str) -> float:
    left_count = max(len(_tokens(left)), 1)
    right_count = max(len(_tokens(right)), 1)
    ratio = min(left_count, right_count) / max(left_count, right_count)
    return ratio


def _strict_length_similarity(left: str, right: str) -> float:
    """More aggressive penalty for length mismatch."""
    left_count = max(len(_tokens(left)), 1)
    right_count = max(len(_tokens(right)), 1)
    ratio = min(left_count, right_count) / max(left_count, right_count)
    # Square to penalise bigger deviations harder
    return ratio**2


def _avg_sentence_length(text: str) -> float:
    sents = _sentences(text)
    if not sents:
        return 0.0
    return mean(len(_tokens(s)) for s in sents)


def _sentence_length_similarity(left: str, right: str) -> float:
    """Compare average sentence length between two texts."""
    avg_l = _avg_sentence_length(left)
    avg_r = _avg_sentence_length(right)
    if avg_l == 0 and avg_r == 0:
        return 1.0
    mx = max(avg_l, avg_r, 1)
    return max(0.0, 1.0 - abs(avg_l - avg_r) / mx)


def _punctuation_similarity(left: str, right: str) -> float:
    marks = ("!", "?", ",", ".", "…", ":", ";")
    left_len = max(len(left), 1)
    right_len = max(len(right), 1)
    similarities: list[float] = []
    for mark in marks:
        left_ratio = left.count(mark) / left_len
        right_ratio = right.count(mark) / right_len
        similarities.append(max(0.0, 1.0 - abs(left_ratio - right_ratio) * 25))
    return mean(similarities) if similarities else 0.0


def _emoji_similarity(left: str, right: str) -> float:
    """Compare emoji usage density."""
    emoji_pat = re.compile(
        r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        r"\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF"
        r"\U00002702-\U000027B0\U0001FA00-\U0001FA6F"
        r"\U0001FA70-\U0001FAFF\U00002600-\U000026FF]"
    )
    left_count = len(emoji_pat.findall(left))
    right_count = len(emoji_pat.findall(right))
    left_len = max(len(left.split()), 1)
    right_len = max(len(right.split()), 1)
    left_density = left_count / left_len
    right_density = right_count / right_len
    # Both have none → perfect match
    if left_count == 0 and right_count == 0:
        return 1.0
    return max(0.0, 1.0 - abs(left_density - right_density) * 15)


def _capitalization_similarity(left: str, right: str) -> float:
    """Compare capitalization style (all lowercase vs proper case)."""
    if not left or not right:
        return 1.0
    left_upper_ratio = sum(1 for c in left if c.isupper()) / max(len(left), 1)
    right_upper_ratio = sum(1 for c in right if c.isupper()) / max(len(right), 1)
    return max(0.0, 1.0 - abs(left_upper_ratio - right_upper_ratio) * 20)


def _abbreviation_density(text: str) -> float:
    """Estimate informal abbreviation density (e.g., cmq, nn, xk, etc.)."""
    abbrev_patterns = re.compile(
        r"\b(cmq|nn|xk|xké|xche|pk|pls|plz|thx|ty|tnx|msg|dm|tbh|imo|btw|ngl"
        r"|idk|omg|lol|lmao|rn|brb|ttyl|hbu|wbu|ily|np|nvm|smh|fr|istg|fyi)\b",
        re.IGNORECASE,
    )
    words = max(len(text.split()), 1)
    hits = len(abbrev_patterns.findall(text))
    return hits / words


def _formality_similarity(left: str, right: str) -> float:
    """Compare formality level based on abbreviation density."""
    ld = _abbreviation_density(left)
    rd = _abbreviation_density(right)
    if ld == 0 and rd == 0:
        return 1.0
    return max(0.0, 1.0 - abs(ld - rd) * 30)


def _vocabulary_richness(text: str) -> float:
    """Type-token ratio."""
    tokens = _tokens(text)
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def _vocabulary_similarity(left: str, right: str) -> float:
    """Compare type-token ratios."""
    vr_l = _vocabulary_richness(left)
    vr_r = _vocabulary_richness(right)
    return max(0.0, 1.0 - abs(vr_l - vr_r) * 5)


# ── Base scoring helpers ─────────────────────────────────


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
    return _clamp(hits / 3)


# ── Gold-answer deep analysis ───────────────────────────


def _deep_gold_analysis(response_text: str, gold_answer: str) -> dict:
    """Run a battery of detailed comparisons when a gold answer is available.

    Returns a dict of named scores (0-1) and a list of textual observations.
    """
    observations: list[str] = []

    # --- Content ---
    unigram_sim = _jaccard_similarity(response_text, gold_answer)
    bigram_sim = _ngram_overlap(response_text, gold_answer, 2)
    trigram_sim = _ngram_overlap(response_text, gold_answer, 3)
    coverage = _content_coverage(gold_answer, response_text)
    content_score = _clamp(
        0.25 * unigram_sim + 0.30 * bigram_sim + 0.20 * trigram_sim + 0.25 * coverage
    )
    if content_score < 0.3:
        observations.append(
            f"Content mismatch: the clone's answer shares very few key phrases "
            f"with your gold answer (overlap {content_score:.0%})."
        )
    elif content_score < 0.55:
        observations.append(
            f"Partial content match ({content_score:.0%}): some ideas are captured but "
            f"important details from your answer are missing."
        )

    # --- Length ---
    length_sim = _strict_length_similarity(response_text, gold_answer)
    resp_words = len(_tokens(response_text))
    gold_words = len(_tokens(gold_answer))
    if length_sim < 0.5:
        observations.append(
            f"Length mismatch: your answer has {gold_words} words, "
            f"the clone wrote {resp_words} — "
            f"{'way too long' if resp_words > gold_words else 'too short'}."
        )
    elif length_sim < 0.75:
        observations.append(
            f"Length differs: you used {gold_words} words vs clone's {resp_words}."
        )

    # --- Grammar / sentence structure ---
    sent_len_sim = _sentence_length_similarity(response_text, gold_answer)
    if sent_len_sim < 0.5:
        gold_avg = _avg_sentence_length(gold_answer)
        resp_avg = _avg_sentence_length(response_text)
        observations.append(
            f"Sentence structure differs: your avg sentence is ~{gold_avg:.0f} words, "
            f"clone uses ~{resp_avg:.0f} words per sentence."
        )

    # --- Punctuation ---
    punct_sim = _punctuation_similarity(response_text, gold_answer)
    if punct_sim < 0.5:
        observations.append(
            "Punctuation style differs significantly (e.g., comma/period/exclamation usage)."
        )

    # --- Emoji ---
    emoji_sim = _emoji_similarity(response_text, gold_answer)
    if emoji_sim < 0.6:
        observations.append(
            "Emoji usage doesn't match your style "
            "(clone uses too many or too few compared to your answer)."
        )

    # --- Capitalization ---
    cap_sim = _capitalization_similarity(response_text, gold_answer)
    if cap_sim < 0.6:
        observations.append(
            "Capitalization style mismatch (e.g., you write in lowercase but clone capitalises)."
        )

    # --- Formality / abbreviations ---
    formality_sim = _formality_similarity(response_text, gold_answer)
    if formality_sim < 0.5:
        gold_abbr = _abbreviation_density(gold_answer)
        resp_abbr = _abbreviation_density(response_text)
        if gold_abbr > resp_abbr:
            observations.append(
                "You use informal abbreviations (e.g., cmq, nn, lol) "
                "but the clone writes more formally."
            )
        else:
            observations.append(
                "The clone uses more informal abbreviations than you do."
            )

    # --- Vocabulary ---
    vocab_sim = _vocabulary_similarity(response_text, gold_answer)
    if vocab_sim < 0.5:
        observations.append(
            "Vocabulary richness differs: your word variety doesn't match the clone's."
        )

    # Composite gold score (stricter than the old single gold_similarity)
    composite = _clamp(
        0.30 * content_score
        + 0.20 * length_sim
        + 0.12 * sent_len_sim
        + 0.10 * punct_sim
        + 0.08 * emoji_sim
        + 0.07 * cap_sim
        + 0.07 * formality_sim
        + 0.06 * vocab_sim
    )

    return {
        "content_score": content_score,
        "length_similarity": length_sim,
        "sentence_structure": sent_len_sim,
        "punctuation_match": punct_sim,
        "emoji_match": emoji_sim,
        "capitalization_match": cap_sim,
        "formality_match": formality_sim,
        "vocabulary_match": vocab_sim,
        "composite": composite,
        "observations": observations,
    }


# ── Improvement suggestions ─────────────────────────────


def _build_suggestions(
    *,
    persona: PersonaCore,
    gold_answer: str | None,
    response_text: str,
    gold_analysis: dict | None,
    scores: dict,
    ai_penalty_val: float,
    never_say_hits: int,
    context_type: str,
) -> list[dict]:
    """Generate actionable improvement suggestions when evaluation is weak."""
    suggestions: list[dict] = []

    # --- Style / writing sample suggestions ---
    if gold_answer and gold_analysis:
        if gold_analysis["length_similarity"] < 0.6:
            gold_words = len(_tokens(gold_answer))
            suggestions.append(
                {
                    "type": "writing_sample",
                    "action": "create",
                    "severity": "high",
                    "title": "Add writing sample with correct length",
                    "reason": (
                        f"Your answers are typically ~{gold_words} words long in this context, "
                        f"but the clone generates responses of a very different length."
                    ),
                    "payload": {
                        "content": gold_answer,
                        "context_type": context_type,
                        "is_representative": True,
                        "notes": f"Reference length: ~{gold_words} words",
                    },
                }
            )

        if gold_analysis["formality_match"] < 0.5:
            gold_abbr = _abbreviation_density(gold_answer)
            suggestions.append(
                {
                    "type": "memory",
                    "action": "create",
                    "severity": "high",
                    "title": "Record writing formality preference",
                    "reason": (
                        "The clone doesn't match your formality level — "
                        "you write more casually/informally but the clone is too formal, "
                        "or vice versa."
                    ),
                    "payload": {
                        "memory_type": "style",
                        "title": "Writing formality preference",
                        "content": (
                            f"I write {'informally with abbreviations' if gold_abbr > 0.02 else 'with a more formal tone'}. "
                            f'Example: "{gold_answer[:150]}"'
                        ),
                        "source": "testing_lab_auto",
                        "confidence": 0.9,
                        "tags": ["style", "formality"],
                    },
                }
            )

        if gold_analysis["capitalization_match"] < 0.6:
            gold_upper = sum(1 for c in gold_answer if c.isupper()) / max(
                len(gold_answer), 1
            )
            style_desc = (
                "all lowercase" if gold_upper < 0.02 else "normal capitalization"
            )
            suggestions.append(
                {
                    "type": "memory",
                    "action": "create",
                    "severity": "medium",
                    "title": "Record capitalization style",
                    "reason": f"You write in {style_desc} but the clone doesn't match.",
                    "payload": {
                        "memory_type": "style",
                        "title": "Capitalization style",
                        "content": f"I typically write in {style_desc}.",
                        "source": "testing_lab_auto",
                        "confidence": 0.85,
                        "tags": ["style", "capitalization"],
                    },
                }
            )

        if gold_analysis["emoji_match"] < 0.6:
            import re as _re

            emoji_pat = _re.compile(
                r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
                r"\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF"
                r"\U00002702-\U000027B0]"
            )
            gold_emojis = emoji_pat.findall(gold_answer)
            if gold_emojis:
                suggestions.append(
                    {
                        "type": "memory",
                        "action": "create",
                        "severity": "medium",
                        "title": "Record emoji usage style",
                        "reason": "Your emoji usage doesn't match the clone's output.",
                        "payload": {
                            "memory_type": "style",
                            "title": "Emoji usage",
                            "content": f"I use emojis in my messages. Common ones: {' '.join(set(gold_emojis[:10]))}",
                            "source": "testing_lab_auto",
                            "confidence": 0.85,
                            "tags": ["style", "emoji"],
                        },
                    }
                )
            else:
                suggestions.append(
                    {
                        "type": "memory",
                        "action": "create",
                        "severity": "medium",
                        "title": "Record no-emoji preference",
                        "reason": "You don't use emojis but the clone adds them.",
                        "payload": {
                            "memory_type": "style",
                            "title": "No emoji usage",
                            "content": "I rarely or never use emojis in my messages.",
                            "source": "testing_lab_auto",
                            "confidence": 0.85,
                            "tags": ["style", "emoji"],
                        },
                    }
                )

        if gold_analysis["sentence_structure"] < 0.5:
            gold_avg = _avg_sentence_length(gold_answer)
            suggestions.append(
                {
                    "type": "memory",
                    "action": "create",
                    "severity": "medium",
                    "title": "Record sentence length preference",
                    "reason": (
                        f"Your sentences average ~{gold_avg:.0f} words but the clone "
                        f"writes sentences of a very different length."
                    ),
                    "payload": {
                        "memory_type": "style",
                        "title": "Sentence length preference",
                        "content": (
                            f"I tend to write {'short, punchy' if gold_avg < 8 else 'longer, detailed'} "
                            f"sentences (~{gold_avg:.0f} words each)."
                        ),
                        "source": "testing_lab_auto",
                        "confidence": 0.85,
                        "tags": ["style", "sentence_length"],
                    },
                }
            )

        if gold_analysis["content_score"] < 0.4:
            suggestions.append(
                {
                    "type": "writing_sample",
                    "action": "create",
                    "severity": "high",
                    "title": "Add this answer as writing sample",
                    "reason": (
                        "The clone's content doesn't match what you would say. "
                        "Adding your gold answer as a writing sample will help the clone "
                        "learn your typical response patterns."
                    ),
                    "payload": {
                        "content": gold_answer,
                        "context_type": context_type,
                        "is_representative": True,
                        "notes": "Added from Testing Lab — content mismatch fix",
                    },
                }
            )

    # --- AI-ish language ---
    if ai_penalty_val > 0.15:
        ai_phrases_found = [p for p in AIISH_PHRASES if p in response_text.lower()]
        if ai_phrases_found:
            suggestions.append(
                {
                    "type": "never_say",
                    "action": "update",
                    "severity": "high",
                    "title": "Block AI-sounding phrases",
                    "reason": (
                        f"The clone used AI-typical phrases: "
                        f"{', '.join(repr(p) for p in ai_phrases_found[:4])}. "
                        f"Adding them to never_say will prevent this."
                    ),
                    "payload": {
                        "phrases": ai_phrases_found,
                    },
                }
            )

    # --- Never-say violations ---
    if never_say_hits > 0:
        suggestions.append(
            {
                "type": "policy",
                "action": "create",
                "severity": "high",
                "title": "Strengthen never-say enforcement",
                "reason": (
                    f"The clone used {never_say_hits} phrase(s) from the never_say list. "
                    f"Adding a stricter policy rule may help enforcement."
                ),
                "payload": {
                    "policy_type": "guardrail",
                    "name": "Strict never-say enforcement",
                    "description": (
                        "Never use any of the phrases in the persona's never_say list. "
                        "These are explicitly banned expressions."
                    ),
                    "priority": 10,
                },
            }
        )

    # --- Low tone fidelity ---
    if scores.get("tone_fidelity", 1.0) < 0.55:
        suggestions.append(
            {
                "type": "memory",
                "action": "create",
                "severity": "medium",
                "title": "Clarify conversational tone",
                "reason": (
                    "The clone's tone doesn't match yours well. Adding a memory "
                    "about your typical tone in this context will help."
                ),
                "payload": {
                    "memory_type": "style",
                    "title": f"Tone in {context_type} context",
                    "content": (
                        f"In {context_type} conversations, my tone is "
                        f"{'casual and warm' if context_type in ('friend', 'romantic') else 'direct and measured'}. "
                        + (f'Example: "{gold_answer[:120]}"' if gold_answer else "")
                    ),
                    "source": "testing_lab_auto",
                    "confidence": 0.85,
                    "tags": ["tone", context_type],
                },
            }
        )

    # --- Low memory relevance ---
    if scores.get("memory_relevance", 1.0) < 0.4:
        suggestions.append(
            {
                "type": "memory",
                "action": "create",
                "severity": "low",
                "title": "Add more contextual memories",
                "reason": (
                    "Memory relevance is low — the clone may not have enough "
                    "personal knowledge to draw from. Add memories about topics "
                    "you commonly discuss."
                ),
                "payload": {
                    "memory_type": "fact",
                    "title": "Context-relevant knowledge",
                    "content": (
                        "Add specific memories about topics you discuss in "
                        f"{context_type} conversations."
                    ),
                    "source": "testing_lab_auto",
                    "confidence": 0.7,
                    "tags": ["context", context_type],
                },
            }
        )

    return suggestions


# ── Main evaluation builder ──────────────────────────────


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

    # ── Deep gold analysis ───────────────────────────────
    gold_analysis: dict | None = None
    gold_similarity = 0.0
    if gold_answer:
        gold_analysis = _deep_gold_analysis(response_text, gold_answer)
        gold_similarity = gold_analysis["composite"]

    length_score = _length_score(response_text)
    message_overlap = _jaccard_similarity(response_text, request.message)
    memories_count = (
        int(trace.get("memories_count", 0)) if isinstance(trace, dict) else 0
    )
    memory_signal = _clamp(memories_count / 4)
    never_say_hits = sum(
        1
        for phrase in persona.never_say or []
        if phrase and phrase.lower() in response_text.lower()
    )

    emotional_issue = _issue_hit(issues, EMOTIONAL_ISSUE_HINTS)
    hallucination_issue = _issue_hit(issues, HALLUCINATION_HINTS)
    boundary_issue = _issue_hit(issues, BOUNDARY_HINTS)
    ai_penalty_val = _ai_penalty(response_text)

    # ── Compute dimension scores ─────────────────────────
    if gold_answer and gold_analysis:
        # When gold answer is provided, weight gold analysis heavily and be stricter
        style_similarity = _clamp(
            0.35 * style_score
            + 0.20 * gold_analysis["content_score"]
            + 0.15 * gold_analysis["formality_match"]
            + 0.10 * gold_analysis["punctuation_match"]
            + 0.10 * gold_analysis["capitalization_match"]
            + 0.10 * gold_analysis["emoji_match"]
        )
        response_usefulness = _clamp(
            0.30 * gold_analysis["content_score"]
            + 0.25 * gold_analysis["length_similarity"]
            + 0.15 * gold_analysis["sentence_structure"]
            + 0.15 * tone_score
            + 0.10 * gold_analysis["vocabulary_match"]
            + 0.05 * confidence
        )
    else:
        style_similarity = _clamp(0.85 * style_score + 0.15 * length_score)
        response_usefulness = _clamp(
            0.45 * length_score
            + 0.25 * tone_score
            + 0.2 * authenticity_score
            + 0.1 * confidence
        )

    tone_fidelity = _clamp(
        0.75 * tone_score + 0.25 * (1.0 if not emotional_issue else 0.35)
    )
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
        0.40 * (1 - authenticity_score)
        + 0.25 * (1 - style_similarity)
        + 0.25 * ai_penalty_val
        + 0.10 * (1 - length_score)
    )
    emotional_appropriateness = _clamp(
        0.7 * tone_fidelity + 0.3 * (1.0 if not emotional_issue else 0.35)
    )
    boundary_respect = _clamp(
        0.55 * policy_compliance + 0.45 * (1.0 if never_say_hits == 0 else 0.0)
    )

    # ── Overall score ────────────────────────────────────
    dimension_scores = [
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

    if gold_answer:
        # When gold answer is provided, apply a stricter penalty
        raw_overall = mean(dimension_scores)
        # Additional penalty: if gold composite is low, pull overall down
        gold_drag = max(0.0, 0.6 - gold_similarity) * 0.3
        overall_score = _clamp(raw_overall - gold_drag)
    else:
        overall_score = _clamp(mean(dimension_scores))

    # ── Stricter thresholds when gold is provided ────────
    if gold_answer:
        if overall_score >= 0.82:
            verdict = "pass"
        elif overall_score >= 0.62:
            verdict = "mixed"
        else:
            verdict = "fail"
    else:
        if overall_score >= 0.78:
            verdict = "pass"
        elif overall_score >= 0.58:
            verdict = "mixed"
        else:
            verdict = "fail"

    # ── Detailed reviewer notes ──────────────────────────
    notes: list[str] = []
    if gold_answer:
        notes.append(
            f"Evaluated against your gold answer (composite match: {gold_similarity:.0%})."
        )
        if gold_analysis and gold_analysis["observations"]:
            notes.append("Issues found:")
            notes.extend(f"  • {obs}" for obs in gold_analysis["observations"])
    else:
        notes.append("Auto-evaluated from critic scores and response heuristics.")
    if critic_issues:
        notes.append(
            "Critic issues: " + "; ".join(str(issue) for issue in critic_issues[:5])
        )
    if ai_penalty_val > 0.1:
        notes.append(
            "⚠ The response contains AI-sounding phrases that don't match natural human speech."
        )
    if never_say_hits > 0:
        notes.append(
            f"⚠ The response used {never_say_hits} banned phrase(s) from never_say list."
        )

    thumbs: str | None = None
    if overall_score >= 0.72:
        thumbs = "up"
    elif overall_score < 0.5:
        thumbs = "down"

    # ── Build scores dict for suggestion builder ─────────
    all_scores = {
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
    }

    # ── Improvement suggestions (only for non-pass) ──────
    suggestions: list[dict] = []
    if verdict != "pass":
        suggestions = _build_suggestions(
            persona=persona,
            gold_answer=gold_answer,
            response_text=response_text,
            gold_analysis=gold_analysis,
            scores=all_scores,
            ai_penalty_val=ai_penalty_val,
            never_say_hits=never_say_hits,
            context_type=request.context_type,
        )

    return {
        **all_scores,
        "overall_score": overall_score,
        "verdict": verdict,
        "reviewer_notes": "\n".join(notes),
        "thumbs": thumbs,
        "improvement_suggestions": suggestions,
    }
