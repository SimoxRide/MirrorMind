import { useState } from "react";
import { useAppStore } from "../store/useAppStore";
import { testingApi } from "../api/client";
import type { CloneResponse } from "../types";
import TipBox from "../components/TipBox";
import { Send, AlertTriangle, Code2 } from "lucide-react";

const CONTEXT_TYPES = [
    "general",
    "friend",
    "romantic",
    "work",
    "conflict",
    "adversarial",
];

export default function TestingLabPage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const [message, setMessage] = useState("");
    const [context, setContext] = useState("general");
    const [goldAnswer, setGoldAnswer] = useState("");
    const [response, setResponse] = useState<CloneResponse | null>(null);
    const [loading, setLoading] = useState(false);

    const handleRun = async () => {
        if (!activePersonaId || !message) return;
        setLoading(true);
        setResponse(null);
        try {
            const result = await testingApi.runClone({
                persona_id: activePersonaId,
                message,
                context_type: context,
            });
            setResponse(result);
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
                        reply, for comparison
                    </li>
                </ul>
                <p className="mt-2">
                    Check the <strong>Generation Trace</strong> to see what
                    memories, policies, and graph context the clone used.
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
                        Your Gold Answer (optional — for comparison)
                    </label>
                    <textarea
                        className="input min-h-[80px]"
                        value={goldAnswer}
                        onChange={(e) => setGoldAnswer(e.target.value)}
                        placeholder="How would YOU actually reply?"
                    />
                </div>

                <button
                    onClick={handleRun}
                    disabled={loading || !message}
                    className="btn-primary"
                >
                    <Send className="w-4 h-4" />{" "}
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
                        <div className="mt-3 flex gap-4 text-xs text-slate-500">
                            <span>
                                Confidence:{" "}
                                <strong className="text-white">
                                    {(response.confidence * 100).toFixed(0)}%
                                </strong>
                            </span>
                            {response.requires_review && (
                                <span className="text-amber-400 font-medium flex items-center gap-1">
                                    <AlertTriangle className="w-3.5 h-3.5" />{" "}
                                    Requires review
                                </span>
                            )}
                        </div>
                    </div>

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
                                <Code2 className="w-4 h-4 text-slate-400" />{" "}
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
