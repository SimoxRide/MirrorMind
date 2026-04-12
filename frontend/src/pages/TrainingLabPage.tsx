import { useState } from "react";
import { useAppStore } from "../store/useAppStore";
import { trainingApi } from "../api/client";
import type { TrainingQuestion, AnalysisResult } from "../types";
import TipBox from "../components/TipBox";
import {
    Play,
    Send,
    ArrowRight,
    RotateCcw,
    CheckCircle2,
    Brain,
    BookOpen,
    Shield,
    Sparkles,
} from "lucide-react";

const CATEGORIES = [
    "daily_life",
    "emotional",
    "social",
    "conflict",
    "decision",
    "humor",
];

export default function TrainingLabPage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const [questions, setQuestions] = useState<TrainingQuestion[]>([]);
    const [currentIdx, setCurrentIdx] = useState(0);
    const [answer, setAnswer] = useState("");
    const [loading, setLoading] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
    const [count, setCount] = useState(5);
    const [selectedCats, setSelectedCats] = useState<string[]>([]);
    const [autoSave, setAutoSave] = useState(true);
    const [completedCount, setCompletedCount] = useState(0);
    const [sessionLog, setSessionLog] = useState<
        {
            question: string;
            summary: string;
            saved_counts: Record<string, number>;
        }[]
    >([]);
    const [allAskedQuestions, setAllAskedQuestions] = useState<string[]>([]);

    const currentQ = questions[currentIdx] ?? null;

    const handleGenerateQuestions = async () => {
        if (!activePersonaId) return;
        setLoading(true);
        setAnalysis(null);
        setAnswer("");
        setCurrentIdx(0);
        setSessionLog([]);
        setCompletedCount(0);
        try {
            const qs = await trainingApi.generateQuestions({
                persona_id: activePersonaId,
                count,
                categories: selectedCats.length > 0 ? selectedCats : undefined,
                previous_questions: allAskedQuestions,
            });
            setQuestions(qs);
            setAllAskedQuestions((prev) => [
                ...prev,
                ...qs.map((q) => q.question),
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmitAnswer = async () => {
        if (!activePersonaId || !currentQ || !answer.trim()) return;
        setAnalyzing(true);
        setAnalysis(null);
        try {
            const result = await trainingApi.analyzeAnswer({
                persona_id: activePersonaId,
                question: currentQ.question,
                category: currentQ.category,
                context_type: currentQ.context_type,
                answer,
                auto_save: autoSave,
            });
            setAnalysis(result);
            setCompletedCount((c) => c + 1);
            setSessionLog((log) => [
                ...log,
                {
                    question: currentQ.question,
                    summary: result.summary,
                    saved_counts: result.saved_counts,
                },
            ]);
        } finally {
            setAnalyzing(false);
        }
    };

    const handleNext = () => {
        setAnalysis(null);
        setAnswer("");
        if (currentIdx < questions.length - 1) setCurrentIdx(currentIdx + 1);
    };

    const toggleCat = (cat: string) => {
        setSelectedCats((prev) =>
            prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat],
        );
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
            <h2 className="page-header">Training Lab</h2>

            <TipBox title="Training Lab — insegna al clone chi sei">
                <p className="mb-2">
                    Il Training Lab ti fa delle{" "}
                    <strong>domande su scenari di vita quotidiana</strong> e
                    analizza le tue risposte per estrarre automaticamente:
                </p>
                <ul className="list-disc list-inside space-y-1">
                    <li>
                        <strong>Writing Samples</strong> — come scriveresti
                        realmente in quel contesto
                    </li>
                    <li>
                        <strong>Memories</strong> — preferenze, abitudini,
                        relazioni
                    </li>
                    <li>
                        <strong>Policies</strong> — regole comportamentali
                        implicite
                    </li>
                    <li>
                        <strong>Traits</strong> — tratti di personalit&agrave;
                    </li>
                </ul>
                <p className="mt-2">
                    <strong>Come usarlo:</strong> Genera domande, rispondi come
                    faresti nella vita reale, l'AI analizza e salva tutto
                    automaticamente.
                </p>
            </TipBox>

            {/* Session setup */}
            {questions.length === 0 && (
                <div className="card p-6 space-y-5">
                    <h3 className="font-semibold text-white">
                        Start a Training Session
                    </h3>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Number of questions
                        </label>
                        <input
                            type="number"
                            min={1}
                            max={20}
                            className="input w-24"
                            value={count}
                            onChange={(e) =>
                                setCount(parseInt(e.target.value) || 5)
                            }
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Focus categories (optional)
                        </label>
                        <div className="flex gap-2 flex-wrap">
                            {CATEGORIES.map((cat) => (
                                <button
                                    key={cat}
                                    onClick={() => toggleCat(cat)}
                                    className={
                                        selectedCats.includes(cat)
                                            ? "badge-indigo cursor-pointer"
                                            : "badge-slate cursor-pointer hover:bg-slate-600/60"
                                    }
                                >
                                    {cat.replace("_", " ")}
                                </button>
                            ))}
                        </div>
                    </div>

                    <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={autoSave}
                            onChange={(e) => setAutoSave(e.target.checked)}
                            className="rounded bg-slate-700 border-slate-600 text-indigo-500 focus:ring-indigo-500/40"
                        />
                        Auto-save extracted data (memories, writing samples,
                        policies)
                    </label>

                    <button
                        onClick={handleGenerateQuestions}
                        disabled={loading}
                        className="btn-primary"
                    >
                        <Play className="w-4 h-4" />{" "}
                        {loading
                            ? "Generating questions..."
                            : "Start Training Session"}
                    </button>
                </div>
            )}

            {/* Active training session */}
            {questions.length > 0 && currentQ && (
                <div className="space-y-4">
                    {/* Progress bar */}
                    <div className="card p-4">
                        <div className="flex items-center justify-between text-sm text-slate-400 mb-2">
                            <span>
                                Question {currentIdx + 1} / {questions.length}
                            </span>
                            <span>{completedCount} completed</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                            <div
                                className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full h-2 transition-all"
                                style={{
                                    width: `${((currentIdx + (analysis ? 1 : 0)) / questions.length) * 100}%`,
                                }}
                            />
                        </div>
                    </div>

                    {/* Question card */}
                    <div className="card p-6">
                        <div className="flex items-center gap-2 mb-3">
                            <span className="badge-indigo">
                                {currentQ.category.replace("_", " ")}
                            </span>
                            <span className="badge-slate">
                                {currentQ.context_type}
                            </span>
                        </div>
                        {currentQ.scenario && (
                            <p className="text-sm text-slate-400 italic mb-2">
                                Scenario: {currentQ.scenario}
                            </p>
                        )}
                        <p className="text-base font-medium text-white">
                            {currentQ.question}
                        </p>
                    </div>

                    {/* Answer input */}
                    {!analysis && (
                        <div className="card p-6 space-y-3">
                            <label className="block text-sm font-medium text-slate-300">
                                La tua risposta — scrivi come faresti nella
                                realt&agrave;
                            </label>
                            <textarea
                                className="input min-h-[120px]"
                                value={answer}
                                onChange={(e) => setAnswer(e.target.value)}
                                placeholder="Come risponderesti / reagiresti in questa situazione?"
                            />
                            <button
                                onClick={handleSubmitAnswer}
                                disabled={analyzing || !answer.trim()}
                                className="btn-primary"
                            >
                                <Send className="w-4 h-4" />{" "}
                                {analyzing
                                    ? "Analyzing..."
                                    : "Submit & Analyze"}
                            </button>
                        </div>
                    )}

                    {/* Analysis results */}
                    {analysis && (
                        <div className="space-y-3">
                            <div className="card p-5 border-emerald-500/30 bg-emerald-500/5">
                                <h4 className="font-semibold text-sm text-emerald-400 mb-1 flex items-center gap-2">
                                    <CheckCircle2 className="w-4 h-4" />{" "}
                                    Analysis Summary
                                </h4>
                                <p className="text-sm text-slate-300">
                                    {analysis.summary}
                                </p>
                                {analysis.saved && (
                                    <div className="mt-2 flex gap-3 text-xs text-emerald-400/80">
                                        {Object.entries(analysis.saved_counts)
                                            .filter(([, v]) => v > 0)
                                            .map(([k, v]) => (
                                                <span
                                                    key={k}
                                                    className="badge-emerald"
                                                >
                                                    {v} {k.replace("_", " ")}
                                                </span>
                                            ))}
                                    </div>
                                )}
                            </div>

                            {analysis.writing_samples.length > 0 && (
                                <details className="card p-5 group">
                                    <summary className="font-semibold text-sm cursor-pointer text-white flex items-center gap-2">
                                        <BookOpen className="w-4 h-4 text-indigo-400" />{" "}
                                        Writing Samples (
                                        {analysis.writing_samples.length})
                                    </summary>
                                    <div className="mt-3 space-y-2">
                                        {analysis.writing_samples.map(
                                            (ws, i) => (
                                                <div
                                                    key={i}
                                                    className="bg-slate-800/60 rounded-lg p-3 text-sm"
                                                >
                                                    <div className="flex gap-2 mb-1">
                                                        <span className="badge-indigo">
                                                            {ws.context_type}
                                                        </span>
                                                        {ws.tone && (
                                                            <span className="badge-amber">
                                                                {ws.tone}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="whitespace-pre-wrap text-slate-300">
                                                        {ws.content}
                                                    </p>
                                                </div>
                                            ),
                                        )}
                                    </div>
                                </details>
                            )}

                            {analysis.memories.length > 0 && (
                                <details className="card p-5">
                                    <summary className="font-semibold text-sm cursor-pointer text-white flex items-center gap-2">
                                        <Brain className="w-4 h-4 text-purple-400" />{" "}
                                        Memories ({analysis.memories.length})
                                    </summary>
                                    <div className="mt-3 space-y-2">
                                        {analysis.memories.map((m, i) => (
                                            <div
                                                key={i}
                                                className="bg-slate-800/60 rounded-lg p-3 text-sm"
                                            >
                                                <span className="badge-purple mr-2">
                                                    {m.memory_type}
                                                </span>
                                                <strong className="text-white">
                                                    {m.title}
                                                </strong>
                                                <p className="text-slate-400 mt-1">
                                                    {m.content}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </details>
                            )}

                            {analysis.traits.length > 0 && (
                                <details className="card p-5">
                                    <summary className="font-semibold text-sm cursor-pointer text-white flex items-center gap-2">
                                        <Sparkles className="w-4 h-4 text-amber-400" />{" "}
                                        Traits ({analysis.traits.length})
                                    </summary>
                                    <div className="mt-3 space-y-1">
                                        {analysis.traits.map((t, i) => (
                                            <div
                                                key={i}
                                                className="flex items-center justify-between bg-slate-800/60 rounded-lg p-2.5 text-sm"
                                            >
                                                <span className="text-slate-300">
                                                    <strong className="text-white">
                                                        {t.key}:
                                                    </strong>{" "}
                                                    {t.value}
                                                </span>
                                                <span className="text-xs text-slate-500">
                                                    {(
                                                        t.confidence * 100
                                                    ).toFixed(0)}
                                                    %
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </details>
                            )}

                            {analysis.policies.length > 0 && (
                                <details className="card p-5">
                                    <summary className="font-semibold text-sm cursor-pointer text-white flex items-center gap-2">
                                        <Shield className="w-4 h-4 text-rose-400" />{" "}
                                        Policies ({analysis.policies.length})
                                    </summary>
                                    <div className="mt-3 space-y-1">
                                        {analysis.policies.map((p, i) => (
                                            <div
                                                key={i}
                                                className="bg-slate-800/60 rounded-lg p-3 text-sm"
                                            >
                                                <span className="badge-rose mr-2">
                                                    {p.policy_type}
                                                </span>
                                                <strong className="text-white">
                                                    {p.name}
                                                </strong>
                                                <p className="text-slate-400 mt-1">
                                                    {p.description}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </details>
                            )}

                            <div className="flex gap-3">
                                {currentIdx < questions.length - 1 ? (
                                    <button
                                        onClick={handleNext}
                                        className="btn-primary"
                                    >
                                        <ArrowRight className="w-4 h-4" /> Next
                                        Question
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => {
                                            setQuestions([]);
                                            setCurrentIdx(0);
                                            setAnalysis(null);
                                            setAnswer("");
                                        }}
                                        className="btn-primary"
                                    >
                                        <RotateCcw className="w-4 h-4" /> Finish
                                        & Start New Session
                                    </button>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Session log */}
                    {sessionLog.length > 0 && (
                        <details className="card p-5 mt-4">
                            <summary className="font-semibold text-sm cursor-pointer text-white">
                                Session Log ({sessionLog.length} answers)
                            </summary>
                            <div className="mt-3 space-y-2">
                                {sessionLog.map((entry, i) => (
                                    <div
                                        key={i}
                                        className="bg-slate-800/60 rounded-lg p-3 text-sm"
                                    >
                                        <p className="font-medium text-slate-300">
                                            Q{i + 1}: {entry.question}
                                        </p>
                                        <p className="text-slate-500 mt-1">
                                            {entry.summary}
                                        </p>
                                        <div className="mt-1 flex gap-2 text-xs">
                                            {Object.entries(entry.saved_counts)
                                                .filter(([, v]) => v > 0)
                                                .map(([k, v]) => (
                                                    <span
                                                        key={k}
                                                        className="badge-slate"
                                                    >
                                                        {v}{" "}
                                                        {k.replace("_", " ")}
                                                    </span>
                                                ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </details>
                    )}
                </div>
            )}
        </div>
    );
}
