import { useState, useEffect } from "react";
import { useAppStore } from "../store/useAppStore";
import { writingSampleApi } from "../api/client";
import type { WritingSample } from "../types";
import TipBox from "../components/TipBox";
import {
    Plus,
    X,
    Pencil,
    Trash2,
    ChevronLeft,
    ChevronRight,
} from "lucide-react";

const CONTEXT_TYPES = [
    "general",
    "friend",
    "romantic",
    "work",
    "conflict",
    "casual",
    "formal",
];

const PAGE_SIZE = 15;

export default function WritingStylePage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const [samples, setSamples] = useState<WritingSample[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(0);
    const [showForm, setShowForm] = useState(false);
    const [content, setContent] = useState("");
    const [contextType, setContextType] = useState("general");
    const [tone, setTone] = useState("");
    const [notes, setNotes] = useState("");

    const [editingId, setEditingId] = useState<string | null>(null);
    const [editContent, setEditContent] = useState("");
    const [editContextType, setEditContextType] = useState("general");
    const [editTone, setEditTone] = useState("");
    const [editNotes, setEditNotes] = useState("");

    const load = () => {
        if (!activePersonaId) return;
        writingSampleApi
            .list(activePersonaId, {
                limit: PAGE_SIZE,
                offset: page * PAGE_SIZE,
            })
            .then(({ items, total: t }) => {
                setSamples(items);
                setTotal(t);
            });
    };

    useEffect(load, [activePersonaId, page]);

    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    const handleCreate = async () => {
        if (!activePersonaId || !content) return;
        await writingSampleApi.create({
            persona_id: activePersonaId,
            content,
            context_type: contextType,
            tone: tone || undefined,
            notes: notes || undefined,
        });
        setContent("");
        setTone("");
        setNotes("");
        setShowForm(false);
        load();
    };

    const startEdit = (s: WritingSample) => {
        setEditingId(s.id);
        setEditContent(s.content);
        setEditContextType(s.context_type);
        setEditTone(s.tone ?? "");
        setEditNotes(s.notes ?? "");
    };

    const handleUpdate = async () => {
        if (!editingId || !editContent) return;
        await writingSampleApi.update(editingId, {
            content: editContent,
            context_type: editContextType,
            tone: editTone || undefined,
            notes: editNotes || undefined,
        });
        setEditingId(null);
        load();
    };

    const handleDelete = async (id: string) => {
        if (!confirm("Sei sicuro di voler eliminare questo writing sample?"))
            return;
        await writingSampleApi.delete(id);
        load();
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
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <h2 className="page-header">Writing Style Capture</h2>
                <button
                    onClick={() => setShowForm(!showForm)}
                    className={showForm ? "btn-secondary" : "btn-primary"}
                >
                    {showForm ? (
                        <>
                            <X className="w-4 h-4" /> Cancel
                        </>
                    ) : (
                        <>
                            <Plus className="w-4 h-4" /> Add Sample
                        </>
                    )}
                </button>
            </div>

            <TipBox title="Writing Style — teach the clone how you write">
                <p className="mb-2">
                    Writing samples are <strong>the #1 factor</strong> for
                    making your clone sound like you. Paste real messages,
                    emails, or chat snippets you've actually sent.
                </p>
                <ul className="list-disc list-inside space-y-1">
                    <li>
                        <strong>Context type</strong> — tag each sample:{" "}
                        <em>friend</em>, <em>work</em>, <em>romantic</em>,{" "}
                        <em>formal</em>…
                    </li>
                    <li>
                        <strong>Tone</strong> — optional hint: <em>playful</em>,{" "}
                        <em>serious</em>, <em>sarcastic</em>…
                    </li>
                    <li>
                        <strong>Notes</strong> — add backstory for context
                    </li>
                </ul>
                <p className="mt-2">
                    <strong>Quality matters more than quantity.</strong> 10–20
                    diverse samples is a great start.
                </p>
            </TipBox>

            {showForm && (
                <div className="card p-5 space-y-3">
                    <textarea
                        className="input min-h-[120px]"
                        placeholder="Paste a real message or conversation snippet you wrote..."
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                    />
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <select
                            className="input"
                            value={contextType}
                            onChange={(e) => setContextType(e.target.value)}
                        >
                            {CONTEXT_TYPES.map((t) => (
                                <option key={t} value={t}>
                                    {t}
                                </option>
                            ))}
                        </select>
                        <input
                            className="input"
                            placeholder="Tone (e.g. playful, serious)"
                            value={tone}
                            onChange={(e) => setTone(e.target.value)}
                        />
                        <input
                            className="input"
                            placeholder="Notes"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                        />
                    </div>
                    <button onClick={handleCreate} className="btn-primary">
                        Save Sample
                    </button>
                </div>
            )}

            <div className="space-y-2">
                {samples.map((s) =>
                    editingId === s.id ? (
                        <div
                            key={s.id}
                            className="card p-5 space-y-3 ring-2 ring-indigo-500/40"
                        >
                            <textarea
                                className="input min-h-[120px]"
                                value={editContent}
                                onChange={(e) => setEditContent(e.target.value)}
                            />
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                <select
                                    className="input"
                                    value={editContextType}
                                    onChange={(e) =>
                                        setEditContextType(e.target.value)
                                    }
                                >
                                    {CONTEXT_TYPES.map((t) => (
                                        <option key={t} value={t}>
                                            {t}
                                        </option>
                                    ))}
                                </select>
                                <input
                                    className="input"
                                    placeholder="Tone"
                                    value={editTone}
                                    onChange={(e) =>
                                        setEditTone(e.target.value)
                                    }
                                />
                                <input
                                    className="input"
                                    placeholder="Notes"
                                    value={editNotes}
                                    onChange={(e) =>
                                        setEditNotes(e.target.value)
                                    }
                                />
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleUpdate}
                                    className="btn-primary"
                                >
                                    Save
                                </button>
                                <button
                                    onClick={() => setEditingId(null)}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div key={s.id} className="card-hover p-4">
                            <div className="flex items-center justify-between mb-1.5">
                                <div className="flex items-center gap-2">
                                    <span className="badge-indigo">
                                        {s.context_type}
                                    </span>
                                    {s.tone && (
                                        <span className="badge-amber">
                                            {s.tone}
                                        </span>
                                    )}
                                    {s.is_representative && (
                                        <span className="badge-emerald">
                                            ★ representative
                                        </span>
                                    )}
                                </div>
                                <div className="flex items-center gap-3">
                                    <button
                                        onClick={() => startEdit(s)}
                                        className="text-slate-400 hover:text-indigo-400 transition-colors"
                                        title="Edit"
                                    >
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(s.id)}
                                        className="text-slate-400 hover:text-red-400 transition-colors"
                                        title="Delete"
                                    >
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                            <p className="text-sm text-slate-300 whitespace-pre-wrap line-clamp-4">
                                {s.content}
                            </p>
                            {s.notes && (
                                <p className="text-xs text-slate-500 mt-1.5 italic">
                                    {s.notes}
                                </p>
                            )}
                        </div>
                    ),
                )}
                {samples.length === 0 && (
                    <div className="text-sm text-slate-500 text-center py-12">
                        No writing samples yet. Add real examples of how you
                        write.
                    </div>
                )}
            </div>

            {totalPages > 1 && (
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pt-2">
                    <span className="text-xs text-slate-500">
                        {total} campioni — pagina {page + 1} di {totalPages}
                    </span>
                    <div className="flex gap-1">
                        <button
                            onClick={() => setPage((p) => Math.max(0, p - 1))}
                            disabled={page === 0}
                            className="pagination-btn-inactive disabled:opacity-30"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        {Array.from({ length: totalPages }, (_, i) => (
                            <button
                                key={i}
                                onClick={() => setPage(i)}
                                className={
                                    page === i
                                        ? "pagination-btn-active"
                                        : "pagination-btn-inactive"
                                }
                            >
                                {i + 1}
                            </button>
                        )).slice(
                            Math.max(0, page - 2),
                            Math.min(totalPages, page + 3),
                        )}
                        <button
                            onClick={() =>
                                setPage((p) => Math.min(totalPages - 1, p + 1))
                            }
                            disabled={page >= totalPages - 1}
                            className="pagination-btn-inactive disabled:opacity-30"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
