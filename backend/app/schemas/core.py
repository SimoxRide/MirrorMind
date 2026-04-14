"""Pydantic schemas for Interview, Policy, Testing, Evaluation, AgentConfig."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Interview ────────────────────────────────────────────


class InterviewSessionCreate(BaseModel):
    persona_id: UUID
    title: str = "Untitled Session"


class InterviewSessionRead(BaseModel):
    id: UUID
    persona_id: UUID
    title: str
    status: str
    question_count: int
    answers: list["InterviewAnswerRead"] = []
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class InterviewAnswerCreate(BaseModel):
    session_id: UUID
    order_index: int
    question: str
    answer: str = ""


class InterviewAnswerRead(BaseModel):
    id: UUID
    session_id: UUID
    order_index: int
    question: str
    answer: str
    extracted_traits: dict | None
    trait_approved: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class InterviewAnswerUpdate(BaseModel):
    answer: str | None = None
    trait_approved: bool | None = None


# ── PolicyRule ───────────────────────────────────────────


class PolicyRuleCreate(BaseModel):
    persona_id: UUID
    policy_type: str
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    conditions: dict | None = None
    actions: dict | None = None
    priority: int = 0


class PolicyRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    conditions: dict | None = None
    actions: dict | None = None
    is_active: bool | None = None
    priority: int | None = None


class PolicyRuleRead(BaseModel):
    id: UUID
    persona_id: UUID
    policy_type: str
    name: str
    description: str
    conditions: dict | None
    actions: dict | None
    version: int
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── TestScenario ─────────────────────────────────────────


class TestScenarioCreate(BaseModel):
    persona_id: UUID
    title: str
    description: str = ""
    context_type: str = "general"
    test_mode: str = "single"
    input_message: str
    conversation_history: list[dict] | None = None
    gold_answer: str | None = None
    relationship_info: dict | None = None


class TestScenarioRead(BaseModel):
    id: UUID
    persona_id: UUID
    title: str
    description: str
    context_type: str
    test_mode: str
    input_message: str
    conversation_history: list | None
    gold_answer: str | None
    relationship_info: dict | None
    results: list["TestResultRead"] = []
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class TestResultRead(BaseModel):
    id: UUID
    scenario_id: UUID
    clone_response: str
    variant_index: int
    trace: dict | None
    generation_config: dict | None
    evaluations: list["EvaluationRead"] = []
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Evaluation ───────────────────────────────────────────


class EvaluationCreate(BaseModel):
    test_result_id: UUID
    style_similarity: float | None = None
    tone_fidelity: float | None = None
    persona_consistency: float | None = None
    policy_compliance: float | None = None
    memory_relevance: float | None = None
    hallucination_risk: float | None = None
    artificiality: float | None = None
    emotional_appropriateness: float | None = None
    boundary_respect: float | None = None
    response_usefulness: float | None = None
    overall_score: float | None = None
    verdict: str | None = None
    reviewer_notes: str | None = None
    thumbs: str | None = None


class EvaluationRead(BaseModel):
    id: UUID
    test_result_id: UUID
    style_similarity: float | None
    tone_fidelity: float | None
    persona_consistency: float | None
    policy_compliance: float | None
    memory_relevance: float | None
    hallucination_risk: float | None
    artificiality: float | None
    emotional_appropriateness: float | None
    boundary_respect: float | None
    response_usefulness: float | None
    overall_score: float | None
    verdict: str | None
    reviewer_notes: str | None
    thumbs: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── AgentConfig ──────────────────────────────────────────


class AgentConfigCreate(BaseModel):
    persona_id: UUID
    agent_name: str
    system_prompt: str = ""
    instructions: str = ""
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2048
    retrieval_settings: dict | None = None
    guardrails: dict | None = None
    output_schema: dict | None = None


class AgentConfigUpdate(BaseModel):
    system_prompt: str | None = None
    instructions: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    retrieval_settings: dict | None = None
    guardrails: dict | None = None
    output_schema: dict | None = None
    is_active: bool | None = None


class AgentConfigRead(BaseModel):
    id: UUID
    persona_id: UUID
    agent_name: str
    system_prompt: str
    instructions: str
    model: str
    temperature: float
    max_tokens: int
    retrieval_settings: dict | None
    guardrails: dict | None
    output_schema: dict | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Graph schemas ────────────────────────────────────────


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: dict = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    properties: dict = {}


class GraphSubgraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphQueryRequest(BaseModel):
    persona_id: UUID
    query: str | None = None
    node_type: str | None = None
    depth: int = 2
    limit: int = 100


class GraphNodeUpdate(BaseModel):
    label: str | None = None
    type: str | None = None
    properties: dict | None = None


class GraphEdgeCreate(BaseModel):
    persona_id: UUID
    source: str
    target: str
    type: str
    properties: dict = {}


class GraphEdgeUpdate(BaseModel):
    type: str | None = None
    properties: dict | None = None


# ── Improvement suggestions ──────────────────────────────


class ImprovementSuggestion(BaseModel):
    type: str  # memory, policy, writing_sample, never_say
    action: str  # create, update
    severity: str  # high, medium, low
    title: str
    reason: str
    payload: dict


# ── Clone request / response ────────────────────────────


class CloneRequest(BaseModel):
    persona_id: UUID
    message: str
    context_type: str = "general"
    relationship_info: dict | None = None
    conversation_history: list[dict] | None = None
    autonomy_mode: str = "medium"  # low, medium, high
    scenario_id: UUID | None = None
    gold_answer: str | None = None
    save_result: bool = True


class CloneResponse(BaseModel):
    response: str
    confidence: float
    trace: dict | None = None
    requires_review: bool = False
    alternative_responses: list[str] = []
    test_result_id: UUID | None = None
    evaluation: EvaluationRead | None = None
    improvement_suggestions: list[ImprovementSuggestion] = []
