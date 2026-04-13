import { useState, type ReactNode } from "react";
import {
    AlertCircle,
    Brain,
    Check,
    CopyMinus,
    FileText,
    Shield,
    Sparkles,
    Upload,
} from "lucide-react";
import { ioApi } from "../api/client";
import type { DocumentAnalysis, QuickImportResult } from "../types";
import { useAppStore } from "../store/useAppStore";

const SOURCE_KIND_OPTIONS = [
    { value: "resume_cv", label: "CV / Resume" },
    { value: "biography", label: "Biography" },
    { value: "notes", label: "Personal Notes" },
    { value: "chat_export", label: "Chat Export" },
    { value: "policy_doc", label: "Rules / Policies" },
    { value: "general", label: "General Document" },
];

export default function DocumentImportPage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const personas = useAppStore((s) => s.personas);
    const activePersona = personas.find((p) => p.id === activePersonaId);

    const [file, setFile] = useState<File | null>(null);
    const [sourceKind, setSourceKind] = useState("resume_cv");
    const [notes, setNotes] = useState("");
    const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
    const [error, setError] = useState("");
    const [analyzing, setAnalyzing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [result, setResult] = useState<QuickImportResult | null>(null);

    const handleAnalyze = async () => {
        if (!activePersonaId || !file) return;
        setAnalyzing(true);
        setError("");
        setResult(null);

        try {
            const response = await ioApi.analyzeDocument(activePersonaId, file, {
                sourceKind,
                notes,
            });
            setAnalysis(response);
        } catch (e) {
            setAnalysis(null);
            setError("Document analysis failed. Check the file type and server logs.");
        } finally {
            setAnalyzing(false);
        }
    };

    const handleImport = async () => {
        if (!activePersonaId || !analysis) return;
        setSaving(true);
        setError("");

        try {
            const response = await ioApi.quickImport(
                activePersonaId,
                {
                    persona: analysis.persona,
                    memories: analysis.memories,
                    writing_samples: analysis.writing_samples,
                    policies: analysis.policies,
                },
                analysis.filename,
            );
            setResult(response.imported);
        } catch (e) {
            setError("Import failed. The extracted payload could not be saved.");
        } finally {
            setSaving(false);
        }
    };

    if (!activePersonaId) {
        return (
            <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto">
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-6 text-center">
                    <AlertCircle className="w-8 h-8 text-yellow-400 mx-auto mb-3" />
                    <p className="text-yellow-300">
                        Select a persona from the sidebar to analyze a document.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
            <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-3">
                    <FileText className="w-7 h-7 text-cyan-400" />
                    Document Import
                </h1>
                <p className="text-gray-400 mt-2">
                    Upload PDFs, DOCX files, text notes, markdown, or JSON to
                    extract clone-ready memories, writing style, traits, and
                    policies for{" "}
                    <span className="text-cyan-300 font-medium">
                        {activePersona?.name}
                    </span>
                    .
                </p>
            </div>

            <div className="card p-5 sm:p-6 space-y-5">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Document
                        </label>
                        <input
                            type="file"
                            accept=".pdf,.docx,.txt,.md,.json"
                            onChange={(e) =>
                                setFile(e.target.files?.[0] ?? null)
                            }
                            className="input file:mr-4 file:rounded-lg file:border-0 file:bg-slate-700 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-200 hover:file:bg-slate-600"
                        />
                        <p className="text-xs text-slate-500 mt-2">
                            Supported: PDF, DOCX, TXT, MD, JSON
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Source kind
                        </label>
                        <select
                            value={sourceKind}
                            onChange={(e) => setSourceKind(e.target.value)}
                            className="input-select"
                        >
                            {SOURCE_KIND_OPTIONS.map((option) => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                        Notes for the analyzer
                    </label>
                    <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Example: This is my CV. Extract factual memories, work style, and behavioral rules."
                        className="input min-h-[96px]"
                    />
                </div>

                {error && (
                    <div className="flex items-start gap-2 text-red-400 text-sm">
                        <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                        <span>{error}</span>
                    </div>
                )}

                <button
                    onClick={handleAnalyze}
                    disabled={!file || analyzing}
                    className="btn-primary"
                >
                    <Upload className="w-4 h-4" />
                    {analyzing ? "Analyzing document..." : "Analyze document"}
                </button>
            </div>

            {analysis && (
                <div className="space-y-4">
                    <div className="card p-5 sm:p-6 space-y-4">
                        <div className="flex flex-wrap items-center gap-2">
                            <span className="badge-cyan">{analysis.document_type}</span>
                            <span className="badge-slate">
                                {analysis.source_kind.replace("_", " ")}
                            </span>
                            <span className="badge-slate">
                                {analysis.char_count.toLocaleString()} chars
                            </span>
                            <span className="badge-slate">
                                {analysis.analyzed_chunk_count}/{analysis.chunk_count} chunks
                            </span>
                            {analysis.was_truncated && (
                                <span className="badge-amber">
                                    partial coverage
                                </span>
                            )}
                        </div>

                        <div>
                            <p className="text-sm font-medium text-white">
                                {analysis.filename}
                            </p>
                            <p className="text-sm text-slate-400 mt-1">
                                {analysis.summary || "No summary returned."}
                            </p>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
                            <CountCard
                                icon={<Brain className="w-4 h-4 text-purple-400" />}
                                label="Memories"
                                count={analysis.estimated_new_counts.memories}
                            />
                            <CountCard
                                icon={<Sparkles className="w-4 h-4 text-emerald-400" />}
                                label="Writing Samples"
                                count={analysis.estimated_new_counts.writing_samples}
                            />
                            <CountCard
                                icon={<Shield className="w-4 h-4 text-rose-400" />}
                                label="Policies"
                                count={analysis.estimated_new_counts.policies}
                            />
                            <CountCard
                                icon={<FileText className="w-4 h-4 text-cyan-400" />}
                                label="Traits"
                                count={analysis.traits.length}
                            />
                        </div>

                        {(analysis.persona || analysis.duplicate_counts.memories > 0 ||
                            analysis.duplicate_counts.writing_samples > 0 ||
                            analysis.duplicate_counts.policies > 0) && (
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                                {analysis.persona && (
                                    <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-4">
                                        <p className="text-sm text-cyan-300 font-medium">
                                            {analysis.persona_would_change
                                                ? "Persona fields will be updated"
                                                : "Persona fields already match existing data"}
                                        </p>
                                        <p className="text-xs text-slate-400 mt-1">
                                            Identity, tone, preferences, or boundaries
                                            were inferred from this document.
                                        </p>
                                    </div>
                                )}

                                {(analysis.duplicate_counts.memories > 0 ||
                                    analysis.duplicate_counts.writing_samples > 0 ||
                                    analysis.duplicate_counts.policies > 0) && (
                                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
                                        <p className="text-sm text-amber-300 font-medium flex items-center gap-2">
                                            <CopyMinus className="w-4 h-4" />
                                            Duplicate matches detected
                                        </p>
                                        <p className="text-xs text-slate-400 mt-1">
                                            {analysis.duplicate_counts.memories} memories,{" "}
                                            {analysis.duplicate_counts.writing_samples} writing
                                            samples, {analysis.duplicate_counts.policies} policies
                                            look like duplicates and will be skipped on save.
                                        </p>
                                    </div>
                                )}
                            </div>
                        )}

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <CountCard
                                icon={<Brain className="w-4 h-4 text-purple-400" />}
                                label="Extracted Memories"
                                count={analysis.memories.length}
                            />
                            <CountCard
                                icon={<Sparkles className="w-4 h-4 text-emerald-400" />}
                                label="Extracted Samples"
                                count={analysis.writing_samples.length}
                            />
                            <CountCard
                                icon={<Shield className="w-4 h-4 text-rose-400" />}
                                label="Extracted Policies"
                                count={analysis.policies.length}
                            />
                        </div>

                        <div className="text-xs text-slate-500">
                            {analysis.used_char_count.toLocaleString()} characters analyzed
                            {analysis.was_truncated &&
                                ` out of ${analysis.char_count.toLocaleString()} total.`}
                            {!analysis.was_truncated && " across the full document."}
                        </div>

                        {analysis.persona && (
                            <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-4">
                                <p className="text-sm text-cyan-300 font-medium">
                                    Persona preview
                                </p>
                                <pre className="text-xs text-slate-400 mt-2 whitespace-pre-wrap">
                                    {JSON.stringify(analysis.persona, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>

                    {analysis.traits.length > 0 && (
                        <PreviewSection
                            title="Traits"
                            items={analysis.traits.map(
                                (trait) =>
                                    `${trait.key}: ${trait.value} (${Math.round(trait.confidence * 100)}%)`,
                            )}
                        />
                    )}

                    {analysis.memories.length > 0 && (
                        <PreviewSection
                            title="Memories"
                            items={analysis.memories.map(
                                (memory) =>
                                    `[${memory.memory_type}] ${memory.title}`,
                            )}
                        />
                    )}

                    {analysis.writing_samples.length > 0 && (
                        <PreviewSection
                            title="Writing Samples"
                            items={analysis.writing_samples.map(
                                (sample) =>
                                    `[${sample.context_type}] ${sample.content.slice(0, 90)}${sample.content.length > 90 ? "..." : ""}`,
                            )}
                        />
                    )}

                    {analysis.policies.length > 0 && (
                        <PreviewSection
                            title="Policies"
                            items={analysis.policies.map(
                                (policy) =>
                                    `[${policy.policy_type}] ${policy.name}`,
                            )}
                        />
                    )}

                    <div className="card p-5 sm:p-6">
                        <button
                            onClick={handleImport}
                            disabled={saving}
                            className="btn-primary"
                        >
                            {saving ? (
                                "Saving extracted data..."
                            ) : (
                                <>
                                    <Check className="w-4 h-4" />
                                    Save to {activePersona?.name}
                                </>
                            )}
                        </button>
                    </div>

                    <div>
                        <p className="text-sm font-medium text-slate-300 mb-2">
                            Extracted text preview
                        </p>
                        <pre className="bg-slate-950/80 border border-slate-700 rounded-lg p-4 text-xs text-slate-400 whitespace-pre-wrap max-h-64 overflow-y-auto">
                            {analysis.preview_text}
                        </pre>
                    </div>
                </div>
            )}

            {result && (
                <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-6 text-center space-y-2">
                    <Check className="w-10 h-10 text-green-400 mx-auto" />
                    <p className="text-green-300 font-semibold text-lg">
                        Import complete
                    </p>
                    <p className="text-gray-400 text-sm">
                        {result.memories} memories · {result.writing_samples} writing
                        samples · {result.policies} policies
                        {result.persona_updated && " · persona updated"}
                    </p>
                    {result.skipped_duplicates > 0 && (
                        <p className="text-xs text-slate-500">
                            Skipped {result.skipped_duplicates} duplicates:{" "}
                            {result.duplicate_memories} memories,{" "}
                            {result.duplicate_writing_samples} writing samples,{" "}
                            {result.duplicate_policies} policies.
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}

function CountCard({
    icon,
    label,
    count,
}: {
    icon: ReactNode;
    label: string;
    count: number;
}) {
    return (
        <div className="bg-slate-900/70 border border-slate-700 rounded-lg p-4">
            <div className="flex items-center gap-2 text-sm text-slate-400">
                {icon}
                {label}
            </div>
            <p className="text-2xl font-semibold text-white mt-2">{count}</p>
        </div>
    );
}

function PreviewSection({
    title,
    items,
}: {
    title: string;
    items: string[];
}) {
    return (
        <div className="card p-5 sm:p-6">
            <p className="text-sm font-semibold text-white mb-3">{title}</p>
            <ul className="space-y-2">
                {items.map((item, index) => (
                    <li key={`${title}-${index}`} className="text-sm text-slate-400">
                        • {item}
                    </li>
                ))}
            </ul>
        </div>
    );
}
