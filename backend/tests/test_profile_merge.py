from app.ingestion.profile_merge import (
    build_existing_import_index,
    estimate_import_counts,
    merge_document_payloads,
)


def test_merge_document_payloads_dedupes_chunk_outputs():
    merged = merge_document_payloads(
        [
            {
                "persona": {
                    "identity_summary": "Short summary.",
                    "never_say": ["nope"],
                    "tone": {"default": "warm"},
                },
                "summary": "Chunk one.",
                "memories": [
                    {
                        "memory_type": "long_term",
                        "title": "Worked at ACME",
                        "content": "Worked at ACME as an engineer.",
                        "tags": ["work"],
                    }
                ],
                "writing_samples": [
                    {
                        "content": "Hey, let's sync tomorrow.",
                        "context_type": "work",
                        "tone": "friendly",
                    }
                ],
                "policies": [
                    {
                        "policy_type": "boundary",
                        "name": "No weekend calls",
                        "description": "Avoid calls on weekends.",
                    }
                ],
                "traits": [{"key": "humor", "value": "dry", "confidence": 0.6}],
            },
            {
                "persona": {
                    "identity_summary": "Longer summary with more detail.",
                    "never_say": ["nope", "absolutely not"],
                    "tone": {"when_serious": "direct"},
                },
                "summary": "Chunk two.",
                "memories": [
                    {
                        "memory_type": "long_term",
                        "title": "Worked at ACME",
                        "content": "Worked at ACME as a senior engineer leading projects.",
                        "tags": ["career"],
                    }
                ],
                "writing_samples": [
                    {
                        "content": "Hey, let's sync tomorrow.",
                        "context_type": "general",
                        "tone": None,
                    }
                ],
                "policies": [
                    {
                        "policy_type": "boundary",
                        "name": "No weekend calls",
                        "description": "Avoid work calls on weekends unless urgent.",
                    }
                ],
                "traits": [{"key": "humor", "value": "dry", "confidence": 0.9}],
            },
        ]
    )

    assert merged["persona"]["identity_summary"] == "Longer summary with more detail."
    assert merged["persona"]["never_say"] == ["nope", "absolutely not"]
    assert merged["persona"]["tone"] == {
        "default": "warm",
        "when_serious": "direct",
    }
    assert merged["summary"] == "Chunk one. Chunk two."
    assert len(merged["memories"]) == 1
    assert merged["memories"][0]["content"].endswith("leading projects.")
    assert merged["memories"][0]["tags"] == ["work", "career"]
    assert len(merged["writing_samples"]) == 1
    assert merged["writing_samples"][0]["context_type"] == "work"
    assert len(merged["policies"]) == 1
    assert merged["policies"][0]["description"].endswith("unless urgent.")
    assert len(merged["traits"]) == 1
    assert merged["traits"][0]["confidence"] == 0.9


def test_estimate_import_counts_flags_existing_duplicates():
    data = {
        "memories": [
            {
                "memory_type": "long_term",
                "title": "Worked at ACME",
                "content": "Worked at ACME as an engineer.",
            },
            {
                "memory_type": "project",
                "title": "Built MirrorMind",
                "content": "Built the MirrorMind product.",
            },
        ],
        "writing_samples": [
            {"content": "Hey, let's sync tomorrow.", "context_type": "work"},
            {"content": "Thanks, got it.", "context_type": "general"},
        ],
        "policies": [
            {
                "policy_type": "boundary",
                "name": "No weekend calls",
                "description": "Avoid work calls on weekends.",
            },
            {
                "policy_type": "tone",
                "name": "Be direct",
                "description": "Prefer concise and direct replies.",
            },
        ],
    }
    existing_index = build_existing_import_index(
        [
            {
                "memory_type": "long_term",
                "title": "Worked at ACME",
                "content": "Worked at ACME as an engineer.",
            }
        ],
        [{"content": "Hey, let's sync tomorrow."}],
        [{"policy_type": "boundary", "name": "No weekend calls", "description": ""}],
    )

    new_counts, duplicate_counts = estimate_import_counts(data, existing_index)

    assert new_counts == {"memories": 1, "writing_samples": 1, "policies": 1}
    assert duplicate_counts == {"memories": 1, "writing_samples": 1, "policies": 1}
