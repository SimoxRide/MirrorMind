"""Clone engine — the full pipeline for generating clone responses.

Flow:
1. Classify incoming context
2. Retrieve persona core
3. Retrieve relevant memories
4. Retrieve graph substructure
5. Retrieve similar style examples
6. Apply policy constraints
7. Generate draft response (ResponseGenerator agent)
8. Critique/review (Critic agent)
9. Return final response with trace metadata
"""

import json
import re
from uuid import UUID

from agents import Runner
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.definitions import critic_agent, response_generator_agent
from app.core.logging import get_logger
from app.evaluation.scoring import build_auto_evaluation
from app.graphrag.retrieval import GraphRetriever
from app.models.persona import Memory, PersonaCore, WritingSample
from app.models.policy import PolicyRule
from app.models.testing import Evaluation, TestResult, TestScenario
from app.models.user import User
from app.schemas.core import (
    CloneRequest,
    CloneResponse,
    EvaluationRead,
    ImprovementSuggestion,
)
from app.services.provider_settings import resolve_provider_settings

logger = get_logger("clone_engine")


class CloneEngine:
    """Orchestrates the clone generation pipeline."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.graph_retriever = GraphRetriever()

    async def generate(
        self, req: CloneRequest, user: User | None = None
    ) -> CloneResponse:
        provider_settings = resolve_provider_settings(user)
        if not provider_settings.configured:
            # Fallback: return a placeholder so the pipeline is testable without OpenAI
            return CloneResponse(
                response="[Clone engine requires a configured provider API key to generate responses]",
                confidence=0.0,
                trace={"error": "openai_not_configured"},
                requires_review=True,
            )

        trace: dict = {}

        # Step 1: Load persona
        persona = await self._load_persona(req.persona_id)
        if not persona:
            return CloneResponse(
                response="[Persona not found]",
                confidence=0.0,
                trace={"error": "persona_not_found"},
                requires_review=True,
            )
        trace["persona_name"] = persona.name

        # Step 2: Retrieve memories
        memories = await self._retrieve_memories(req.persona_id, req.context_type)
        trace["memories_count"] = len(memories)

        # Step 3: Retrieve graph context
        keywords = req.message.split()[:10]  # simple keyword extraction
        graph_context = await self.graph_retriever.retrieve_for_context(
            req.persona_id, keywords, limit=10
        )
        trace["graph_nodes_retrieved"] = len(graph_context)

        # Step 4: Retrieve style examples
        style_examples = await self._retrieve_style_examples(
            req.persona_id, req.context_type
        )
        trace["style_examples_count"] = len(style_examples)

        # Step 5: Load policies
        policies = await self._load_policies(req.persona_id)
        trace["policies_count"] = len(policies)

        # Step 6: Assemble context and generate
        context_prompt = self._assemble_context(
            persona=persona,
            memories=memories,
            graph_context=graph_context,
            style_examples=style_examples,
            policies=policies,
            request=req,
        )

        # Step 7: Run response generator agent
        gen_result = await Runner.run(
            response_generator_agent,
            input=context_prompt,
            run_config=provider_settings.to_run_config(),
        )
        gen_output = gen_result.final_output
        trace["raw_generation"] = gen_output

        # Parse generator output
        try:
            gen_data = json.loads(gen_output)
        except (json.JSONDecodeError, TypeError):
            gen_data = {
                "response": gen_output,
                "confidence": 0.5,
                "requires_review": True,
                "reasoning": "Could not parse structured output",
            }

        # Step 8: Run critic agent
        critic_prompt = self._assemble_critic_context(
            persona=persona,
            policies=policies,
            generated_response=gen_data.get("response", gen_output),
            request=req,
        )
        critic_result = await Runner.run(
            critic_agent,
            input=critic_prompt,
            run_config=provider_settings.to_run_config(),
        )
        trace["critic_output"] = critic_result.final_output

        try:
            critic_data = json.loads(critic_result.final_output)
        except (json.JSONDecodeError, TypeError):
            critic_data = {"approved": True, "issues": [], "scores": {}}

        # Use critic's suggested edit if response was not approved
        final_response = gen_data.get("response", gen_output)
        if not critic_data.get("approved", True) and critic_data.get("suggested_edit"):
            final_response = critic_data["suggested_edit"]
            trace["used_critic_edit"] = True

        confidence = gen_data.get("confidence", 0.5)
        requires_review = gen_data.get("requires_review", False) or not critic_data.get(
            "approved", True
        )

        trace["critic_scores"] = critic_data.get("scores", {})
        trace["critic_issues"] = critic_data.get("issues", [])

        test_result_id = None
        evaluation_read = None
        improvement_suggestions: list[ImprovementSuggestion] = []
        if req.save_result:
            scenario = await self._get_or_create_scenario(req)
            test_result = TestResult(
                scenario_id=scenario.id,
                clone_response=final_response,
                variant_index=0,
                trace=trace,
                generation_config={
                    "context_type": req.context_type,
                    "autonomy_mode": req.autonomy_mode,
                    "confidence": confidence,
                    "requires_review": requires_review,
                },
            )
            self.db.add(test_result)
            await self.db.flush()
            await self.db.refresh(test_result)
            test_result_id = test_result.id

            eval_result = build_auto_evaluation(
                persona=persona,
                request=req,
                response_text=final_response,
                confidence=confidence,
                trace=trace,
                gold_answer=scenario.gold_answer,
            )
            # Extract improvement suggestions before persisting evaluation
            raw_suggestions = eval_result.pop("improvement_suggestions", [])
            improvement_suggestions = [
                ImprovementSuggestion(**s) for s in raw_suggestions
            ]

            evaluation = Evaluation(
                test_result_id=test_result.id,
                **eval_result,
            )
            self.db.add(evaluation)
            await self.db.flush()
            await self.db.refresh(evaluation)
            evaluation_read = EvaluationRead.model_validate(evaluation)

        return CloneResponse(
            response=final_response,
            confidence=confidence,
            trace=trace,
            requires_review=requires_review,
            test_result_id=test_result_id,
            evaluation=evaluation_read,
            improvement_suggestions=improvement_suggestions,
        )

    async def _load_persona(self, persona_id: UUID) -> PersonaCore | None:
        return await self.db.get(PersonaCore, persona_id)

    async def _retrieve_memories(
        self, persona_id: UUID, context_type: str
    ) -> list[dict]:
        stmt = (
            select(Memory)
            .where(
                Memory.persona_id == persona_id, Memory.approval_status == "approved"
            )
            .order_by(Memory.confidence.desc())
            .limit(20)
        )
        result = await self.db.execute(stmt)
        memories = result.scalars().all()
        return [
            {
                "title": m.title,
                "content": m.content[:500],
                "type": m.memory_type,
                "confidence": m.confidence,
            }
            for m in memories
        ]

    async def _retrieve_style_examples(
        self, persona_id: UUID, context_type: str
    ) -> list[str]:
        stmt = (
            select(WritingSample)
            .where(
                WritingSample.persona_id == persona_id,
                WritingSample.is_representative.is_(True),
            )
            .limit(10)
        )
        if context_type != "general":
            stmt = stmt.where(WritingSample.context_type == context_type)
        result = await self.db.execute(stmt)
        samples = result.scalars().all()
        return [s.content[:500] for s in samples]

    async def _load_policies(self, persona_id: UUID) -> list[dict]:
        stmt = (
            select(PolicyRule)
            .where(PolicyRule.persona_id == persona_id, PolicyRule.is_active.is_(True))
            .order_by(PolicyRule.priority.desc())
        )
        result = await self.db.execute(stmt)
        policies = result.scalars().all()
        return [
            {
                "type": p.policy_type,
                "name": p.name,
                "description": p.description,
                "conditions": p.conditions,
                "actions": p.actions,
            }
            for p in policies
        ]

    async def _get_or_create_scenario(self, req: CloneRequest) -> TestScenario:
        scenario = None
        if req.scenario_id:
            scenario = await self.db.get(TestScenario, req.scenario_id)

        if scenario:
            if req.gold_answer and req.gold_answer != scenario.gold_answer:
                scenario.gold_answer = req.gold_answer
            if req.relationship_info:
                scenario.relationship_info = req.relationship_info
            if req.conversation_history:
                scenario.conversation_history = req.conversation_history
            await self.db.flush()
            await self.db.refresh(scenario)
            return scenario

        message = re.sub(r"\s+", " ", req.message).strip()
        title_suffix = message[:57] + "..." if len(message) > 60 else message
        scenario = TestScenario(
            persona_id=req.persona_id,
            title=f"{req.context_type.title()}: {title_suffix or 'Untitled test'}",
            description="Auto-saved from Testing Lab.",
            context_type=req.context_type,
            test_mode="single",
            input_message=req.message,
            conversation_history=req.conversation_history,
            gold_answer=req.gold_answer,
            relationship_info=req.relationship_info,
        )
        self.db.add(scenario)
        await self.db.flush()
        await self.db.refresh(scenario)
        return scenario

    def _assemble_context(
        self,
        persona: PersonaCore,
        memories: list[dict],
        graph_context: list[dict],
        style_examples: list[str],
        policies: list[dict],
        request: CloneRequest,
    ) -> str:
        parts = [
            f"=== PERSONA: {persona.name} ===",
            f"Identity: {persona.identity_summary}",
            f"Values: {json.dumps(persona.values or {})}",
            f"Tone: {json.dumps(persona.tone or {})}",
            f"Communication Preferences: {json.dumps(persona.communication_preferences or {})}",
            f"Modes: {json.dumps(persona.modes or {})}",
            f"Never Say: {json.dumps(persona.never_say or [])}",
            f"Autonomy Level: {persona.autonomy_level}",
        ]

        # Style profile — grammar, punctuation, emoji habits, etc.
        if persona.style_profile:
            parts.append("")
            parts.append("=== WRITING STYLE PROFILE ===")
            parts.append("IMPORTANT: Replicate these exact writing habits — grammar, punctuation, capitalization, emoji usage, etc.")
            for key, value in persona.style_profile.items():
                parts.append(f"- {key}: {json.dumps(value) if isinstance(value, (dict, list)) else value}")

        parts.append("")
        parts.append("=== RELEVANT MEMORIES ==="),
        ]
        for m in memories[:10]:
            parts.append(f"- [{m['type']}] {m['title']}: {m['content'][:200]}")

        parts.append("")
        parts.append("=== GRAPH KNOWLEDGE ===")
        for g in graph_context[:10]:
            neighbors_str = ", ".join(
                f"{n.get('name', '?')} ({n.get('rel', '?')})"
                for n in g.get("neighbors", [])[:5]
            )
            parts.append(
                f"- {g.get('name', '?')} [{g.get('type', '?')}] → {neighbors_str}"
            )

        parts.append("")
        parts.append("=== STYLE EXAMPLES ===")
        for ex in style_examples[:5]:
            parts.append(f'  "{ex[:300]}"')

        parts.append("")
        parts.append("=== ACTIVE POLICIES ===")
        for p in policies:
            parts.append(f"- [{p['type']}] {p['name']}: {p['description']}")

        parts.append("")
        parts.append("=== CURRENT CONVERSATION ===")
        parts.append(f"Context: {request.context_type}")
        if request.conversation_history:
            for msg in request.conversation_history[-5:]:
                parts.append(f"  {msg.get('role', 'user')}: {msg.get('content', '')}")
        parts.append(f"  incoming: {request.message}")
        parts.append("")
        parts.append(
            "Now respond AS this person. Output JSON with: response, confidence, requires_review, reasoning."
        )

        return "\n".join(parts)

    def _assemble_critic_context(
        self,
        persona: PersonaCore,
        policies: list[dict],
        generated_response: str,
        request: CloneRequest,
    ) -> str:
        parts = [
            f"=== PERSONA: {persona.name} ===",
            f"Identity: {persona.identity_summary}",
            f"Never Say: {json.dumps(persona.never_say or [])}",
            "",
            "=== POLICIES ===",
        ]
        for p in policies:
            parts.append(f"- [{p['type']}] {p['name']}: {p['description']}")

        parts.append("")
        parts.append(f"=== INCOMING MESSAGE ===\n{request.message}")
        parts.append(f"\n=== GENERATED RESPONSE ===\n{generated_response}")
        parts.append(
            "\nReview this response. Output JSON with: approved, issues, scores, suggested_edit."
        )

        return "\n".join(parts)
