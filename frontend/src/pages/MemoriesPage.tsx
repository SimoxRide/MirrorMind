import { useEffect, useState } from "react";
import { useAppStore } from "../store/useAppStore";
import { memoryApi } from "../api/client";
import type { Memory, MemoryCreate } from "../types";
import TipBox from "../components/TipBox";
import {
    Plus,
    X,
    Pencil,
    Trash2,
    ChevronLeft,
    ChevronRight,
} from "lucide-react";

const MEMORY_TYPES = [
    "long_term",
    "episodic",
    "relational",
    "preference",
    "project",
    "style",
    "decision",
];

const TYPE_BADGE: Record<string, string> = {
    long_term: "badge-indigo",
    episodic: "badge-purple",
    relational: "badge-rose",
    preference: "badge-amber",
    project: "badge-emerald",
    style: "badge-cyan",
    decision: "badge-slate",
};

const PAGE_SIZE = 15;

export default function MemoriesPage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const [memories, setMemories] = useState<Memory[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(0);
    const [filterType, setFilterType] = useState<string>("");
    const [showForm, setShowForm] = useState(false);

    const [title, setTitle] = useState("");
    const [content, setContent] = useState("");
    const [memType, setMemType] = useState("long_term");
    const [tags, setTags] = useState("");
    const [linkedEntities, setLinkedEntities] = useState("");

    const [editingId, setEditingId] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState("");
    const [editContent, setEditContent] = useState("");
    const [editMemType, setEditMemType] = useState("long_term");
    const [editTags, setEditTags] = useState("");
    const [editLinkedEntities, setEditLinkedEntities] = useState("");

    const load = () => {
        if (!activePersonaId) return;
        memoryApi
            .list(activePersonaId, {
                ...(filterType ? { memory_type: filterType } : {}),
                limit: PAGE_SIZE,
                offset: page * PAGE_SIZE,
            })
            .then(({ items, total: t }) => {
                setMemories(items);
                setTotal(t);
            });
    };

    useEffect(load, [activePersonaId, filterType, page]);

    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    const handleCreate = async () => {
        if (!activePersonaId || !title || !content) return;
        const data: MemoryCreate = {
            persona_id: activePersonaId,
            memory_type: memType,
            title,
            content,
            tags: tags ? tags.split(",").map((t) => t.trim()) : undefined,
            linked_entities: linkedEntities
                ? linkedEntities.split(",").map((e) => e.trim())
                : undefined,
        };
        await memoryApi.create(data);
        setTitle("");
        setContent("");
        setTags("");
        setLinkedEntities("");
        setShowForm(false);
        load();
    };

    const startEdit = (m: Memory) => {
        setEditingId(m.id);
        setEditTitle(m.title);
        setEditContent(m.content);
        setEditMemType(m.memory_type);
        setEditTags((m.tags ?? []).join(", "));
        setEditLinkedEntities((m.linked_entities ?? []).join(", "));
    };

    const handleUpdate = async () => {
        if (!editingId || !editTitle || !editContent) return;
        await memoryApi.update(editingId, {
            title: editTitle,
            content: editContent,
            memory_type: editMemType,
            tags: editTags ? editTags.split(",").map((t) => t.trim()) : [],
            linked_entities: editLinkedEntities
                ? editLinkedEntities.split(",").map((e) => e.trim())
                : [],
        });
        setEditingId(null);
        load();
    };

    const handleDelete = async (id: string) => {
        if (!confirm("Sei sicuro di voler eliminare questa memoria?")) return;
        await memoryApi.delete(id);
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
                <h2 className="page-header">Memories & Knowledge</h2>
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
                            <Plus className="w-4 h-4" /> Add Memory
                        </>
                    )}
                </button>
            </div>

            <TipBox title="Memories & Knowledge — what goes here?">
                <p className="mb-2">
                    Memories are the <strong>knowledge base</strong> your clone
                    draws from when generating responses. The more relevant
                    memories, the more authentic the clone sounds.
                </p>
                <ul className="list-disc list-inside space-y-1">
                    <li>
                        <strong>Long-term</strong> — core facts: background,
                        education, career, expertise
                    </li>
                    <li>
                        <strong>Episodic</strong> — specific events and stories
                    </li>
                    <li>
                        <strong>Relational</strong> — info about people you know
                    </li>
                    <li>
                        <strong>Preference</strong> — likes, dislikes, opinions
                    </li>
                    <li>
                        <strong>Project</strong> — ongoing work and goals
                    </li>
                    <li>
                        <strong>Style</strong> — communication habits
                    </li>
                    <li>
                        <strong>Decision</strong> — past choices and reasoning
                    </li>
                </ul>
                <p className="mt-2">
                    <strong>Pro tip:</strong> Use tags and linked entities to
                    make memories easier to find.
                </p>
            </TipBox>

            {/* Filter */}
            <div className="flex gap-2 flex-wrap">
                <button
                    onClick={() => {
                        setFilterType("");
                        setPage(0);
                    }}
                    className={
                        !filterType
                            ? "badge-indigo"
                            : "badge-slate cursor-pointer hover:bg-slate-600/60"
                    }
                >
                    All
                </button>
                {MEMORY_TYPES.map((t) => (
                    <button
                        key={t}
                        onClick={() => {
                            setFilterType(t);
                            setPage(0);
                        }}
                        className={
                            filterType === t
                                ? TYPE_BADGE[t] || "badge-indigo"
                                : "badge-slate cursor-pointer hover:bg-slate-600/60"
                        }
                    >
                        {t.replace("_", " ")}
                    </button>
                ))}
            </div>

            {/* Create form */}
            {showForm && (
                <div className="card p-5 space-y-3">
                    <input
                        className="input"
                        placeholder="Title"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                    />
                    <textarea
                        className="input min-h-[80px]"
                        placeholder="Content"
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                    />
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <select
                            className="input"
                            value={memType}
                            onChange={(e) => setMemType(e.target.value)}
                        >
                            {MEMORY_TYPES.map((t) => (
                                <option key={t} value={t}>
                                    {t.replace("_", " ")}
                                </option>
                            ))}
                        </select>
                        <input
                            className="input"
                            placeholder="Tags (comma-separated)"
                            value={tags}
                            onChange={(e) => setTags(e.target.value)}
                        />
                    </div>
                    <input
                        className="input"
                        placeholder="Linked entities (comma-separated)"
                        value={linkedEntities}
                        onChange={(e) => setLinkedEntities(e.target.value)}
                    />
                    <button onClick={handleCreate} className="btn-primary">
                        Save Memory
                    </button>
                </div>
            )}

            {/* List */}
            <div className="space-y-2">
                {memories.map((m) =>
                    editingId === m.id ? (
                        <div
                            key={m.id}
                            className="card p-5 space-y-3 ring-2 ring-indigo-500/40"
                        >
                            <input
                                className="input"
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                            />
                            <textarea
                                className="input min-h-[80px]"
                                value={editContent}
                                onChange={(e) => setEditContent(e.target.value)}
                            />
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <select
                                    className="input"
                                    value={editMemType}
                                    onChange={(e) =>
                                        setEditMemType(e.target.value)
                                    }
                                >
                                    {MEMORY_TYPES.map((t) => (
                                        <option key={t} value={t}>
                                            {t.replace("_", " ")}
                                        </option>
                                    ))}
                                </select>
                                <input
                                    className="input"
                                    placeholder="Tags (comma-separated)"
                                    value={editTags}
                                    onChange={(e) =>
                                        setEditTags(e.target.value)
                                    }
                                />
                            </div>
                            <input
                                className="input"
                                placeholder="Linked entities (comma-separated)"
                                value={editLinkedEntities}
                                onChange={(e) =>
                                    setEditLinkedEntities(e.target.value)
                                }
                            />
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
                        <div key={m.id} className="card-hover p-4">
                            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <span
                                        className={
                                            TYPE_BADGE[m.memory_type] ||
                                            "badge-slate"
                                        }
                                    >
                                        {m.memory_type.replace("_", " ")}
                                    </span>
                                    <span className="font-medium text-sm text-white">
                                        {m.title}
                                    </span>
                                </div>
                                <div className="flex items-center gap-3 flex-shrink-0">
                                    <span className="text-xs text-slate-500">
                                        conf: {m.confidence.toFixed(1)}
                                    </span>
                                    <button
                                        onClick={() => startEdit(m)}
                                        className="text-slate-400 hover:text-indigo-400 transition-colors"
                                        title="Edit"
                                    >
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(m.id)}
                                        className="text-slate-400 hover:text-red-400 transition-colors"
                                        title="Delete"
                                    >
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                            <p className="text-sm text-slate-400 mt-1.5 line-clamp-2">
                                {m.content}
                            </p>
                            {m.tags && m.tags.length > 0 && (
                                <div className="mt-2 flex gap-1 flex-wrap">
                                    {m.tags.map((t, i) => (
                                        <span key={i} className="badge-cyan">
                                            {t}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    ),
                )}
                {memories.length === 0 && (
                    <div className="text-sm text-slate-500 text-center py-12">
                        No memories yet.
                    </div>
                )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pt-2">
                    <span className="text-xs text-slate-500">
                        {total} memorie — pagina {page + 1} di {totalPages}
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
