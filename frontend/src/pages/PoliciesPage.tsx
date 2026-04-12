import { useEffect, useState } from "react";
import { useAppStore } from "../store/useAppStore";
import { policyApi } from "../api/client";
import type { PolicyRule } from "../types";
import TipBox from "../components/TipBox";
import {
    Plus,
    X,
    Pencil,
    Trash2,
    ChevronLeft,
    ChevronRight,
} from "lucide-react";

const POLICY_TYPES = [
    "tone",
    "risk_tolerance",
    "escalation",
    "flirting",
    "work_communication",
    "conflict_handling",
    "uncertainty",
    "forbidden_pattern",
    "ask_before_send",
    "human_review_required",
];

const PAGE_SIZE = 15;

export default function PoliciesPage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const [policies, setPolicies] = useState<PolicyRule[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(0);
    const [showForm, setShowForm] = useState(false);
    const [name, setName] = useState("");
    const [pType, setPType] = useState("tone");
    const [description, setDescription] = useState("");
    const [priority, setPriority] = useState(0);

    const [editingId, setEditingId] = useState<string | null>(null);
    const [editName, setEditName] = useState("");
    const [editPType, setEditPType] = useState("tone");
    const [editDescription, setEditDescription] = useState("");
    const [editPriority, setEditPriority] = useState(0);

    const load = () => {
        if (!activePersonaId) return;
        policyApi
            .list(activePersonaId, {
                limit: PAGE_SIZE,
                offset: page * PAGE_SIZE,
            })
            .then(({ items, total: t }) => {
                setPolicies(items);
                setTotal(t);
            });
    };

    useEffect(load, [activePersonaId, page]);

    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    const handleCreate = async () => {
        if (!activePersonaId || !name) return;
        await policyApi.create({
            persona_id: activePersonaId,
            policy_type: pType,
            name,
            description,
            priority,
        });
        setName("");
        setDescription("");
        setShowForm(false);
        load();
    };

    const startEdit = (p: PolicyRule) => {
        setEditingId(p.id);
        setEditName(p.name);
        setEditPType(p.policy_type);
        setEditDescription(p.description ?? "");
        setEditPriority(p.priority);
    };

    const handleUpdate = async () => {
        if (!editingId || !editName) return;
        await policyApi.update(editingId, {
            name: editName,
            policy_type: editPType,
            description: editDescription,
            priority: editPriority,
        });
        setEditingId(null);
        load();
    };

    const handleDelete = async (id: string) => {
        if (!confirm("Sei sicuro di voler eliminare questa policy?")) return;
        await policyApi.delete(id);
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
                <h2 className="page-header">Rules, Values & Policies</h2>
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
                            <Plus className="w-4 h-4" /> Add Policy
                        </>
                    )}
                </button>
            </div>

            <TipBox
                title="Policies — your clone's behavioral rules"
                variant="warning"
            >
                <p className="mb-2">
                    Policies are <strong>hard rules</strong> the clone must
                    follow, regardless of what it learned. Think of them as
                    ethical and behavioral guardrails.
                </p>
                <ul className="list-disc list-inside space-y-1">
                    <li>
                        <strong>tone</strong> — default tone rules
                    </li>
                    <li>
                        <strong>risk_tolerance</strong> — how much risk in
                        responses
                    </li>
                    <li>
                        <strong>escalation</strong> — when to flag to the real
                        you
                    </li>
                    <li>
                        <strong>flirting</strong> — boundaries for romantic
                        interactions
                    </li>
                    <li>
                        <strong>forbidden_pattern</strong> — phrases or
                        behaviors to never use
                    </li>
                    <li>
                        <strong>ask_before_send / human_review_required</strong>{" "}
                        — scenarios needing approval
                    </li>
                </ul>
                <p className="mt-2">
                    <strong>Priority</strong> determines precedence when
                    policies conflict — higher number wins.
                </p>
            </TipBox>

            {showForm && (
                <div className="card p-5 space-y-3">
                    <input
                        className="input"
                        placeholder="Policy name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                    />
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <select
                            className="input"
                            value={pType}
                            onChange={(e) => setPType(e.target.value)}
                        >
                            {POLICY_TYPES.map((t) => (
                                <option key={t} value={t}>
                                    {t.replace(/_/g, " ")}
                                </option>
                            ))}
                        </select>
                        <input
                            type="number"
                            className="input"
                            placeholder="Priority"
                            value={priority}
                            onChange={(e) =>
                                setPriority(parseInt(e.target.value) || 0)
                            }
                        />
                    </div>
                    <textarea
                        className="input min-h-[80px]"
                        placeholder="Description / rule details"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                    />
                    <button onClick={handleCreate} className="btn-primary">
                        Save Policy
                    </button>
                </div>
            )}

            <div className="space-y-2">
                {policies.map((p) =>
                    editingId === p.id ? (
                        <div
                            key={p.id}
                            className="card p-5 space-y-3 ring-2 ring-indigo-500/40"
                        >
                            <input
                                className="input"
                                value={editName}
                                onChange={(e) => setEditName(e.target.value)}
                            />
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <select
                                    className="input"
                                    value={editPType}
                                    onChange={(e) =>
                                        setEditPType(e.target.value)
                                    }
                                >
                                    {POLICY_TYPES.map((t) => (
                                        <option key={t} value={t}>
                                            {t.replace(/_/g, " ")}
                                        </option>
                                    ))}
                                </select>
                                <input
                                    type="number"
                                    className="input"
                                    placeholder="Priority"
                                    value={editPriority}
                                    onChange={(e) =>
                                        setEditPriority(
                                            parseInt(e.target.value) || 0,
                                        )
                                    }
                                />
                            </div>
                            <textarea
                                className="input min-h-[80px]"
                                placeholder="Description / rule details"
                                value={editDescription}
                                onChange={(e) =>
                                    setEditDescription(e.target.value)
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
                        <div key={p.id} className="card-hover p-4">
                            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <span className="badge-purple">
                                        {p.policy_type.replace(/_/g, " ")}
                                    </span>
                                    <span className="font-medium text-sm text-white">
                                        {p.name}
                                    </span>
                                </div>
                                <div className="flex items-center gap-3 flex-shrink-0 flex-wrap">
                                    <span className="text-xs text-slate-500">
                                        v{p.version}
                                    </span>
                                    <span className="text-xs text-slate-500">
                                        pri: {p.priority}
                                    </span>
                                    <span
                                        className={
                                            p.is_active
                                                ? "badge-emerald"
                                                : "badge-rose"
                                        }
                                    >
                                        {p.is_active ? "active" : "inactive"}
                                    </span>
                                    <button
                                        onClick={() => startEdit(p)}
                                        className="text-slate-400 hover:text-indigo-400 transition-colors"
                                        title="Edit"
                                    >
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(p.id)}
                                        className="text-slate-400 hover:text-red-400 transition-colors"
                                        title="Delete"
                                    >
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                            {p.description && (
                                <p className="text-sm text-slate-400 mt-1.5">
                                    {p.description}
                                </p>
                            )}
                        </div>
                    ),
                )}
                {policies.length === 0 && (
                    <div className="text-sm text-slate-500 text-center py-12">
                        No policies defined yet.
                    </div>
                )}
            </div>

            {totalPages > 1 && (
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pt-2">
                    <span className="text-xs text-slate-500">
                        {total} policy — pagina {page + 1} di {totalPages}
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
