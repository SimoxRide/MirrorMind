import { useEffect, useMemo, useState } from "react";
import { BarChart3, RefreshCw } from "lucide-react";
import TipBox from "../components/TipBox";
import { testingApi } from "../api/client";
import { useAppStore } from "../store/useAppStore";
import type { Evaluation, TestResult, TestScenario } from "../types";

type MetricKey =
    | "style_similarity"
    | "tone_fidelity"
    | "persona_consistency"
    | "policy_compliance"
    | "memory_relevance"
    | "hallucination_risk"
    | "artificiality"
    | "emotional_appropriateness"
    | "boundary_respect"
    | "response_usefulness"
    | "overall_score";

type EvaluationRow = {
    scenario: TestScenario;
    result: TestResult;
    evaluation: Evaluation;
};

const METRICS: Array<{
    key: MetricKey;
    name: string;
    desc: string;
    lowerBetter?: boolean;
}> = [
    {
        key: "style_similarity",
        name: "Style Similarity",
        desc: "Does the clone write like you?",
    },
    {
        key: "tone_fidelity",
        name: "Tone Fidelity",
        desc: "Matches emotional tone for context",
    },
    {
        key: "persona_consistency",
        name: "Persona Consistency",
        desc: "Stays in character with identity",
    },
    {
        key: "policy_compliance",
        name: "Policy Compliance",
        desc: "Respects all defined rules",
    },
    {
        key: "memory_relevance",
        name: "Memory Relevance",
        desc: "Pulls the right memories",
    },
    {
        key: "hallucination_risk",
        name: "Hallucination Risk",
        desc: "Invents facts? lower is better",
        lowerBetter: true,
    },
    {
        key: "artificiality",
        name: "Artificiality",
        desc: "Sounds robotic? lower is better",
        lowerBetter: true,
    },
    {
        key: "emotional_appropriateness",
        name: "Emotional Appropriateness",
        desc: "Right emotional response",
    },
    {
        key: "boundary_respect",
        name: "Boundary Respect",
        desc: "Honors never-say and avoid-topics",
    },
    {
        key: "response_usefulness",
        name: "Response Usefulness",
        desc: "Is the reply helpful?",
    },
];

function average(values: Array<number | null | undefined>) {
    const numericValues = values.filter(
        (value): value is number => typeof value === "number",
    );
    if (numericValues.length === 0) return null;
    return (
        numericValues.reduce((total, value) => total + value, 0) /
        numericValues.length
    );
}

function formatScore(score: number | null) {
    if (score === null) return "—";
    return `${Math.round(score * 100)}%`;
}

function scoreClass(score: number | null, lowerBetter = false) {
    if (score === null) return "text-slate-600";
    const normalized = lowerBetter ? 1 - score : score;
    if (normalized >= 0.78) return "text-emerald-400";
    if (normalized >= 0.58) return "text-amber-400";
    return "text-rose-400";
}

function verdictClass(verdict: string | null) {
    if (verdict === "pass") return "badge-emerald";
    if (verdict === "fail") return "badge-rose";
    return "badge-amber";
}

export default function EvaluationPage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const [scenarios, setScenarios] = useState<TestScenario[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const loadScenarios = async () => {
        if (!activePersonaId) return;
        setLoading(true);
        setError("");
        try {
            const data = await testingApi.listScenarios(activePersonaId);
            setScenarios(data);
        } catch (err: unknown) {
            const msg =
                (err as { response?: { data?: { detail?: string } } })?.response
                    ?.data?.detail || "Unable to load evaluation history";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!activePersonaId) {
            setScenarios([]);
            return;
        }
        void loadScenarios();
    }, [activePersonaId]);

    const rows = useMemo<EvaluationRow[]>(() => {
        return scenarios
            .flatMap((scenario) =>
                scenario.results.flatMap((result) => {
                    const latestEvaluation = [...result.evaluations].sort(
                        (left, right) =>
                            new Date(right.created_at).getTime() -
                            new Date(left.created_at).getTime(),
                    )[0];
                    if (!latestEvaluation) return [];
                    return [{ scenario, result, evaluation: latestEvaluation }];
                }),
            )
            .sort(
                (left, right) =>
                    new Date(right.result.created_at).getTime() -
                    new Date(left.result.created_at).getTime(),
            );
    }, [scenarios]);

    const summary = useMemo(() => {
        const overall = average(rows.map((row) => row.evaluation.overall_score));
        const passCount = rows.filter(
            (row) => row.evaluation.verdict === "pass",
        ).length;
        const needsAttention = rows.filter((row) => {
            const overallScore = row.evaluation.overall_score ?? 0;
            return row.evaluation.verdict === "fail" || overallScore < 0.58;
        }).length;

        return {
            totalRuns: rows.length,
            overall,
            passRate: rows.length ? passCount / rows.length : null,
            needsAttention,
        };
    }, [rows]);

    const metricAverages = useMemo(() => {
        const entries = METRICS.map((metric) => [
            metric.key,
            average(rows.map((row) => row.evaluation[metric.key])),
        ]);
        return Object.fromEntries(entries) as Record<MetricKey, number | null>;
    }, [rows]);

    if (!activePersonaId) {
        return (
            <div className="p-4 sm:p-8 text-slate-500">
                Select a persona first.
            </div>
        );
    }

    return (
        <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="page-header">Evaluation & Scoring</h2>
                <button
                    onClick={() => void loadScenarios()}
                    disabled={loading}
                    className="btn-secondary"
                >
                    <RefreshCw
                        className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
                    />
                    Refresh
                </button>
            </div>

            <TipBox title="Evaluation — how good is your clone?">
                <p className="mb-2">
                    Every Testing Lab run is now stored with an automatic
                    evaluation. Scores get sharper when you provide a gold
                    answer.
                </p>
                <p className="mt-2">
                    Use the metrics below to spot weak areas quickly, then rerun
                    tests after adjusting persona, memories, style samples, or
                    policies.
                </p>
            </TipBox>

            {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-sm text-red-400">
                    {error}
                </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="stat-card">
                    <span className="stat-label">Evaluated Runs</span>
                    <span className="stat-value">{summary.totalRuns}</span>
                    <span className="stat-sub">Latest saved testing results</span>
                </div>
                <div className="stat-card">
                    <span className="stat-label">Average Overall</span>
                    <span
                        className={`stat-value ${scoreClass(summary.overall)}`}
                    >
                        {formatScore(summary.overall)}
                    </span>
                    <span className="stat-sub">
                        Aggregate score across the latest evaluation per run
                    </span>
                </div>
                <div className="stat-card">
                    <span className="stat-label">Pass Rate</span>
                    <span
                        className={`stat-value ${scoreClass(summary.passRate)}`}
                    >
                        {formatScore(summary.passRate)}
                    </span>
                    <span className="stat-sub">
                        {summary.needsAttention} run
                        {summary.needsAttention === 1 ? "" : "s"} need attention
                    </span>
                </div>
            </div>

            <div className="card p-6">
                <h3 className="font-semibold text-white mb-5 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-indigo-400" />
                    Evaluation Metrics
                </h3>

                {rows.length === 0 ? (
                    <p className="text-sm text-slate-500">
                        No saved evaluations yet. Run a test in the Testing Lab
                        to populate this dashboard.
                    </p>
                ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                        {METRICS.map((metric) => (
                            <div
                                key={metric.key}
                                className="bg-slate-800/60 rounded-lg p-4"
                            >
                                <div className="text-xs text-slate-500 mb-1 font-medium">
                                    {metric.name}
                                </div>
                                <div
                                    className={`text-2xl font-mono my-1 ${scoreClass(
                                        metricAverages[metric.key],
                                        metric.lowerBetter,
                                    )}`}
                                >
                                    {formatScore(metricAverages[metric.key])}
                                </div>
                                <div className="text-[11px] text-slate-600">
                                    {metric.desc}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {rows.length > 0 && (
                <div className="card p-6">
                    <h3 className="font-semibold text-white mb-4">
                        Recent Evaluations
                    </h3>
                    <div className="space-y-3">
                        {rows.slice(0, 8).map((row) => (
                            <div
                                key={row.result.id}
                                className="bg-slate-800/60 rounded-lg p-4"
                            >
                                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                                    <div className="space-y-2">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className="text-sm font-medium text-white">
                                                {row.scenario.title}
                                            </span>
                                            <span className="badge-slate">
                                                {row.scenario.context_type}
                                            </span>
                                            <span
                                                className={`badge ${verdictClass(row.evaluation.verdict)}`}
                                            >
                                                {row.evaluation.verdict || "mixed"}
                                            </span>
                                        </div>
                                        <p className="text-sm text-slate-400">
                                            {row.scenario.input_message}
                                        </p>
                                        <div className="text-xs text-slate-500">
                                            {new Date(
                                                row.result.created_at,
                                            ).toLocaleString()}
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3 min-w-[220px]">
                                        <div>
                                            <div className="text-xs text-slate-500">
                                                Overall
                                            </div>
                                            <div
                                                className={`text-lg font-semibold ${scoreClass(
                                                    row.evaluation.overall_score,
                                                )}`}
                                            >
                                                {formatScore(
                                                    row.evaluation.overall_score,
                                                )}
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-slate-500">
                                                Usefulness
                                            </div>
                                            <div
                                                className={`text-lg font-semibold ${scoreClass(
                                                    row.evaluation.response_usefulness,
                                                )}`}
                                            >
                                                {formatScore(
                                                    row.evaluation.response_usefulness,
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
