// Core domain types matching backend Pydantic schemas

// ── Auth ────────────────────────────────────────────────

export interface AuthToken {
    access_token: string;
    token_type: string;
    is_admin: boolean;
    email: string;
}

export interface SetupStatus {
    needs_setup: boolean;
}

// ── Production Clones ───────────────────────────────────

export interface ProductionClone {
    id: string;
    persona_id: string;
    persona_name: string;
    is_active: boolean;
    require_api_key: boolean;
    api_key: string | null;
    endpoint_id: string;
    created_at: string;
    updated_at: string;
}

export interface PersonaCore {
    id: string;
    name: string;
    identity_summary: string;
    version: number;
    is_active: boolean;
    values: Record<string, unknown> | null;
    tone: Record<string, unknown> | null;
    humor_style: Record<string, unknown> | null;
    communication_preferences: Record<string, unknown> | null;
    emotional_patterns: Record<string, unknown> | null;
    modes: Record<string, unknown> | null;
    never_say: string[] | null;
    avoid_topics: string[] | null;
    ask_before_acting: string[] | null;
    confidence_threshold: number | null;
    autonomy_level: string;
    created_at: string;
    updated_at: string;
}

export interface PersonaCoreCreate {
    name: string;
    identity_summary?: string;
    values?: Record<string, unknown>;
    tone?: Record<string, unknown>;
    humor_style?: Record<string, unknown>;
    communication_preferences?: Record<string, unknown>;
    emotional_patterns?: Record<string, unknown>;
    modes?: Record<string, unknown>;
    never_say?: string[];
    avoid_topics?: string[];
    ask_before_acting?: string[];
    confidence_threshold?: number;
    autonomy_level?: string;
}

export interface Memory {
    id: string;
    persona_id: string;
    memory_type: string;
    title: string;
    content: string;
    source: string;
    confidence: number;
    date_start: string | null;
    date_end: string | null;
    tags: string[] | null;
    linked_entities: string[] | null;
    approval_status: string;
    metadata_extra: Record<string, unknown> | null;
    created_at: string;
    updated_at: string;
}

export interface MemoryCreate {
    persona_id: string;
    memory_type: string;
    title: string;
    content: string;
    source?: string;
    confidence?: number;
    tags?: string[];
    linked_entities?: string[];
}

export interface WritingSample {
    id: string;
    persona_id: string;
    content: string;
    context_type: string;
    target_person_type: string | null;
    emotional_intensity: string | null;
    tone: string | null;
    is_representative: boolean;
    notes: string | null;
    style_features: Record<string, unknown> | null;
    created_at: string;
}

export interface PolicyRule {
    id: string;
    persona_id: string;
    policy_type: string;
    name: string;
    description: string;
    conditions: Record<string, unknown> | null;
    actions: Record<string, unknown> | null;
    version: number;
    is_active: boolean;
    priority: number;
    created_at: string;
}

export interface TestScenario {
    id: string;
    persona_id: string;
    title: string;
    description: string;
    context_type: string;
    test_mode: string;
    input_message: string;
    conversation_history: Record<string, unknown>[] | null;
    gold_answer: string | null;
    relationship_info: Record<string, unknown> | null;
    results: TestResult[];
    created_at: string;
}

export interface TestResult {
    id: string;
    scenario_id: string;
    clone_response: string;
    variant_index: number;
    trace: Record<string, unknown> | null;
    evaluations: Evaluation[];
    created_at: string;
}

export interface Evaluation {
    id: string;
    test_result_id: string;
    style_similarity: number | null;
    tone_fidelity: number | null;
    persona_consistency: number | null;
    policy_compliance: number | null;
    memory_relevance: number | null;
    hallucination_risk: number | null;
    artificiality: number | null;
    emotional_appropriateness: number | null;
    boundary_respect: number | null;
    response_usefulness: number | null;
    overall_score: number | null;
    verdict: string | null;
    reviewer_notes: string | null;
    thumbs: string | null;
    created_at: string;
}

export interface GraphNode {
    id: string;
    label: string;
    type: string;
    properties: Record<string, unknown>;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    type: string;
    properties: Record<string, unknown>;
}

export interface GraphSubgraph {
    nodes: GraphNode[];
    edges: GraphEdge[];
}

export interface RebuildProgress {
    current: number;
    total: number;
    percent: number;
    current_memory: string;
    status: "processing" | "done";
}

export interface CloneRequest {
    persona_id: string;
    message: string;
    context_type?: string;
    relationship_info?: Record<string, unknown>;
    conversation_history?: Record<string, unknown>[];
    autonomy_mode?: string;
}

export interface CloneResponse {
    response: string;
    confidence: number;
    trace: Record<string, unknown> | null;
    requires_review: boolean;
    alternative_responses: string[];
}

export interface HealthStatus {
    status: string;
    version: string;
}

// ── Training Lab ────────────────────────────────────────

export interface TrainingQuestion {
    question: string;
    category: string;
    context_type: string;
    scenario: string;
}

export interface ExtractedWritingSample {
    content: string;
    context_type: string;
    tone: string | null;
    notes: string | null;
}

export interface ExtractedMemory {
    title: string;
    content: string;
    memory_type: string;
    tags: string[] | null;
    linked_entities: string[] | null;
}

export interface ExtractedTrait {
    key: string;
    value: string;
    confidence: number;
}

export interface ExtractedPolicy {
    name: string;
    policy_type: string;
    description: string;
}

export interface AnalysisResult {
    writing_samples: ExtractedWritingSample[];
    memories: ExtractedMemory[];
    traits: ExtractedTrait[];
    policies: ExtractedPolicy[];
    summary: string;
    saved: boolean;
    saved_counts: Record<string, number>;
}
