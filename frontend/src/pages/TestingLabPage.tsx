import { useState } from "react";
import { Link } from "react-router-dom";
import { useAppStore } from "../store/useAppStore";
import { testingApi } from "../api/client";
import type { CloneResponse } from "../types";
import TipBox from "../components/TipBox";
import {
    Send,
    AlertTriangle,
    Code2,
    CheckCircle2,
    ArrowRight,
} from "lucide-react";

const CONTEXT_TYPES = [
    "general",
    "friend",
    "romantic",
    "work",
    "conflict",
    "adversarial",
];

type QuickMetricKey =
    | "overall_score"
    | "style_similarity"
    | "tone_fidelity"
    | "policy_compliance"
    | "response_usefulness"
    | "hallucination_risk";

const QUICK_METRICS: Array<{
    key: QuickMetricKey;
    label: string;
    lowerBetter?: boolean;
}> = [
    { key: "overall_score", label: "Overall" },
    { key: "style_similarity", label: "Style" },
    { key: "tone_fidelity", label: "Tone" },
    { key: "policy_compliance", label: "Policy" },
    { key: "response_usefulness", label: "Usefulness" },
    { key: "hallucination_risk", label: "Risk", lowerBetter: true },
];

function scoreClass(score: number | null, lowerBetter = false) {
    if (score === null) return "text-slate-500";
    const normalized = lowerBetter ? 1 - score : score;
    if (normalized >= 0.78) return "text-emerald-400";
    if (normalized >= 0.58) return "text-amber-400";
    return "text-rose-400";
}

function formatScore(score: number | null) {
    if (score === null) return "—";
    return `${Math.round(score * 100)}%`;
}

function verdictClass(verdict: string | null) {
    if (verdict === "pass") return "badge-emerald";
    if (verdict === "fail") return "badge-rose";
    return "badge-amber";
}

export default function TestingLabPage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const [message, setMessage] = useState("");
    const [context, setContext] = useState("general");
    const [goldAnswer, setGoldAnswer] = useState("");
    const [response, setResponse] = useState<CloneResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleRun = async () => {
        if (!activePersonaId || !message) return;
        setLoading(true);
        setResponse(null);
        setError("");
        try {
            const result = await testingApi.runClone({
                persona_id: activePersonaId,
                message,
                context_type: context,
                gold_answer: goldAnswer || undefined,
                save_result: true,
            });
            setResponse(result);
        } catch (err: unknown) {
            const msg =
                (err as { response?: { data?: { detail?: string } } })?.response
                    ?.data?.detail || "Testing run failed";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    if (!activePersonaId) {
        return (
            <div className="p-4 sm:p-8 text-slate-500">
                Select a persona first.
            </div>
        );
    }

    return (
        <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
            <h2 className="page-header">Testing Lab</h2>

            <TipBox title="Testing Lab — put your clone to the test">
                <p className="mb-2">
                    This is where you <strong>validate</strong> whether your
                    clone sounds like you.
                </p>
                <ul className="list-disc list-inside space-y-1">
                    <li>
                        <strong>Incoming Message</strong> — write what someone
                        would send you
                    </li>
                    <li>
                        <strong>Context</strong> — relationship context (friend,
                        work, conflict...)
                    </li>
                    <li>
                        <strong>Gold Answer</strong> — how YOU would actually
                        reply, used for auto-scoring
                    </li>
                </ul>
                <p className="mt-2">
                    Each run is now saved automatically and appears in the
                    Evaluation dashboard.
                </p>
            </TipBox>

            <div className="card p-6 space-y-4">
                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Incoming Message
                    </label>
                    <textarea
                        className="input min-h-[100px]"
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder="Type a message that someone would send to you..."
                    />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">
                            Context
                        </label>
                        <select
                            className="input"
                            value={context}
                            onChange={(e) => setContext(e.target.value)}
                        >
                            {CONTEXT_TYPES.map((c) => (
                                <option key={c} value={c}>
                                    {c}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Your Gold Answer (optional, but recommended)
                    </label>
                    <textarea
                        className="input min-h-[80px]"
                        value={goldAnswer}
                        onChange={(e) => setGoldAnswer(e.target.value)}
                        placeholder="How would YOU actually reply?"
                    />
                </div>

                {error && (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-sm text-red-400">
                        {error}
                    </div>
                )}

                <button
                    onClick={handleRun}
                    disabled={loading || !message}
                    className="btn-primary"
                >
                    <Send className="w-4 h-4" />
                    {loading ? "Generating..." : "Run Clone"}
                </button>
            </div>

            {response && (
                <div className="space-y-4">
                    <div className="card p-6">
                        <h3 className="font-semibold text-sm text-white mb-3">
                            Clone Response
                        </h3>
                        <div className="bg-slate-800/80 rounded-lg p-4 text-sm text-slate-200 whitespace-pre-wrap">
                            {response.response}
                        </div>
                        <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
                            <span>
                                Confidence:{" "}
                                <strong className="text-white">
                                    {(response.confidence * 100).toFixed(0)}%
                                </strong>
                            </span>
                            {response.requires_review && (
                                <span className="text-amber-400 font-medium flex items-center gap-1">
                                    <AlertTriangle className="w-3.5 h-3.5" />
                                    Requires review
                                </span>
                            )}
                            {response.test_result_id && (
                                <span className="text-emerald-400 font-medium flex items-center gap-1">
                                    <CheckCircle2 className="w-3.5 h-3.5" />
                                    Saved to Evaluation
                                </span>
                            )}
                        </div>
                    </div>

                    {response.evaluation && (
                        <div className="card p-6 space-y-4">
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                    <h3 className="font-semibold text-sm text-white">
                                        Auto Evaluation
                                    </h3>
                                    <p className="text-sm text-slate-500 mt-1">
                                        This run was scored and stored in the
                                        evaluation history.
                                    </p>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span
                                        className={`badge ${verdictClass(response.evaluation.verdict)}`}
                                    >
                                        {response.evaluation.verdict || "mixed"}
                                    </span>
                                    <Link
                                        to="/evaluation"
                                        className="btn-ghost"
                                    >
                                        Open dashboard
                                        <ArrowRight className="w-4 h-4" />
                                    </Link>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
                                {QUICK_METRICS.map(
                                    ({ key, label, lowerBetter }) => (
                                        <div
                                            key={key}
                                            className="bg-slate-800/60 rounded-lg p-3"
                                        >
                                            <div className="text-xs text-slate-500">
                                                {label}
                                            </div>
                                            <div
                                                className={`text-xl font-semibold mt-1 ${scoreClass(
                                                    response.evaluation?.[key] ??
                                                        null,
                                                    lowerBetter,
                                                )}`}
                                            >
                                                {formatScore(
                                                    response.evaluation?.[key] ??
                                                        null,
                                                )}
                                            </div>
                                            <div className="text-[11px] text-slate-600 mt-1">
                                                {lowerBetter
                                                    ? "lower is better"
                                                    : "higher is better"}
                                            </div>
                                        </div>
                                    ),
                                )}
                            </div>

                            {response.evaluation.reviewer_notes && (
                                <div className="bg-slate-800/80 rounded-lg p-4 text-sm text-slate-300">
                                    {response.evaluation.reviewer_notes}
                                </div>
                            )}
                        </div>
                    )}

                    {goldAnswer && (
                        <div className="card p-6">
                            <h3 className="font-semibold text-sm text-white mb-3">
                                Side-by-Side Comparison
                            </h3>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1.5">
                                        YOUR ANSWER
                                    </div>
                                    <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-sm text-slate-200 whitespace-pre-wrap">
                                        {goldAnswer}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1.5">
                                        CLONE ANSWER
                                    </div>
                                    <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-3 text-sm text-slate-200 whitespace-pre-wrap">
                                        {response.response}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {response.trace && (
                        <details className="card p-6">
                            <summary className="font-semibold text-sm cursor-pointer text-white flex items-center gap-2">
                                <Code2 className="w-4 h-4 text-slate-400" />
                                Generation Trace
                            </summary>
                            <pre className="mt-3 text-xs bg-slate-800/80 rounded-lg p-4 overflow-x-auto text-slate-300 font-mono">
                                {JSON.stringify(response.trace, null, 2)}
                            </pre>
                        </details>
                    )}
                </div>
            )}
        </div>
    );
}
