import { useEffect, useState } from "react";
import { useAppStore } from "../store/useAppStore";
import {
    memoryApi,
    personaApi,
    writingSampleApi,
    policyApi,
} from "../api/client";
import TipBox from "../components/TipBox";
import {
    Brain,
    PenTool,
    Shield,
    Gauge,
    Plus,
    Trash2,
    UserCircle,
} from "lucide-react";

export default function DashboardPage() {
    const personas = useAppStore((s) => s.personas);
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const setActivePersona = useAppStore((s) => s.setActivePersona);
    const fetchPersonas = useAppStore((s) => s.fetchPersonas);
    const activePersona = personas.find((p) => p.id === activePersonaId);
    const [memoryCount, setMemoryCount] = useState(0);
    const [sampleCount, setSampleCount] = useState(0);
    const [policyCount, setPolicyCount] = useState(0);
    const [showNewForm, setShowNewForm] = useState(false);
    const [newName, setNewName] = useState("");
    const [creating, setCreating] = useState(false);

    useEffect(() => {
        if (activePersonaId) {
            memoryApi
                .list(activePersonaId, { limit: 1 })
                .then(({ total }) => setMemoryCount(total));
            writingSampleApi
                .list(activePersonaId, { limit: 1 })
                .then(({ total }) => setSampleCount(total));
            policyApi
                .list(activePersonaId, { limit: 1 })
                .then(({ total }) => setPolicyCount(total));
        }
    }, [activePersonaId]);

    const handleCreatePersona = async () => {
        if (!newName.trim()) return;
        setCreating(true);
        try {
            const p = await personaApi.create({ name: newName.trim() });
            await fetchPersonas();
            setActivePersona(p.id);
            setNewName("");
            setShowNewForm(false);
        } finally {
            setCreating(false);
        }
    };

    const handleDeletePersona = async (id: string) => {
        if (
            !confirm(
                "Sei sicuro di voler eliminare questo profilo e tutti i suoi dati?",
            )
        )
            return;
        await personaApi.delete(id);
        await fetchPersonas();
        if (activePersonaId === id) {
            setActivePersona(personas.find((p) => p.id !== id)?.id ?? null);
        }
    };

    return (
        <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto">
            <h2 className="page-header mb-6">Dashboard</h2>

            <TipBox title="Welcome to MirrorMind" defaultOpen={false}>
                <p className="mb-2">
                    Your{" "}
                    <strong className="text-slate-300">command center</strong>{" "}
                    for building virtual clones. Create{" "}
                    <strong className="text-slate-300">
                        multiple profiles
                    </strong>{" "}
                    — one for each person you want to clone.
                </p>
            </TipBox>

            {/* Profiles */}
            <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                        Profiles ({personas.length})
                    </h3>
                    <button
                        onClick={() => setShowNewForm(!showNewForm)}
                        className="btn-primary text-xs"
                    >
                        <Plus size={14} />
                        {showNewForm ? "Cancel" : "New Profile"}
                    </button>
                </div>

                {showNewForm && (
                    <div className="card p-5 mb-4 flex flex-col sm:flex-row gap-3 sm:items-end">
                        <div className="flex-1">
                            <label className="block text-xs font-medium text-slate-400 mb-1.5">
                                Name of the person to clone
                            </label>
                            <input
                                type="text"
                                className="input"
                                value={newName}
                                onChange={(e) => setNewName(e.target.value)}
                                placeholder="e.g. Simone, Marco, Elena..."
                                onKeyDown={(e) =>
                                    e.key === "Enter" && handleCreatePersona()
                                }
                            />
                        </div>
                        <button
                            onClick={handleCreatePersona}
                            disabled={creating || !newName.trim()}
                            className="btn-primary"
                        >
                            {creating ? "Creating..." : "Create"}
                        </button>
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {personas.map((p) => (
                        <div
                            key={p.id}
                            onClick={() => setActivePersona(p.id)}
                            className={`card-hover p-4 cursor-pointer ${p.id === activePersonaId ? "!border-indigo-500/50 bg-indigo-500/5" : ""}`}
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-3">
                                    <div
                                        className={`w-9 h-9 rounded-lg flex items-center justify-center ${p.id === activePersonaId ? "bg-indigo-500/20" : "bg-slate-700/50"}`}
                                    >
                                        <UserCircle
                                            size={18}
                                            className={
                                                p.id === activePersonaId
                                                    ? "text-indigo-400"
                                                    : "text-slate-500"
                                            }
                                        />
                                    </div>
                                    <div>
                                        <div className="font-semibold text-sm text-white">
                                            {p.name}
                                        </div>
                                        <div className="text-xs text-slate-500 mt-0.5">
                                            v{p.version} · {p.autonomy_level}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    {p.id === activePersonaId && (
                                        <span className="badge-indigo">
                                            active
                                        </span>
                                    )}
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDeletePersona(p.id);
                                        }}
                                        className="text-slate-600 hover:text-red-400 transition-colors p-1"
                                        title="Delete"
                                    >
                                        <Trash2 size={13} />
                                    </button>
                                </div>
                            </div>
                            {p.identity_summary && (
                                <p className="text-xs text-slate-500 mt-2.5 line-clamp-2 pl-12">
                                    {p.identity_summary}
                                </p>
                            )}
                        </div>
                    ))}
                    {personas.length === 0 && (
                        <div className="col-span-full text-center text-slate-600 py-12">
                            No profiles yet. Create one to start cloning.
                        </div>
                    )}
                </div>
            </div>

            {/* Stats */}
            {activePersona && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
                    <StatCard
                        icon={Brain}
                        label="Memories"
                        value={memoryCount}
                        sub="records"
                        color="indigo"
                    />
                    <StatCard
                        icon={PenTool}
                        label="Writing Samples"
                        value={sampleCount}
                        sub="examples"
                        color="emerald"
                    />
                    <StatCard
                        icon={Shield}
                        label="Policies"
                        value={policyCount}
                        sub="rules"
                        color="amber"
                    />
                    <StatCard
                        icon={Gauge}
                        label="Autonomy"
                        value={activePersona.autonomy_level}
                        sub={`threshold: ${activePersona.confidence_threshold}`}
                        color="cyan"
                    />
                </div>
            )}

            {/* Getting started */}
            <div className="card p-6">
                <h3 className="text-sm font-semibold text-white mb-4">
                    Getting Started
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[
                        {
                            step: "1",
                            title: "Create & Configure",
                            desc: "Create a profile and define the core persona identity",
                        },
                        {
                            step: "2",
                            title: "Train & Build",
                            desc: "Run Training Lab sessions, add writing samples, build memories",
                        },
                        {
                            step: "3",
                            title: "Test & Refine",
                            desc: "Test the clone, evaluate results, and iterate",
                        },
                    ].map((item) => (
                        <div key={item.step} className="flex gap-3">
                            <div className="w-7 h-7 rounded-full bg-indigo-500/15 text-indigo-400 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                                {item.step}
                            </div>
                            <div>
                                <div className="text-sm font-medium text-slate-300">
                                    {item.title}
                                </div>
                                <div className="text-xs text-slate-500 mt-0.5">
                                    {item.desc}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

function StatCard({
    icon: Icon,
    label,
    value,
    sub,
    color,
}: {
    icon: React.ElementType;
    label: string;
    value: string | number;
    sub: string;
    color: string;
}) {
    const c: Record<string, string> = {
        indigo: "text-indigo-400 bg-indigo-500/10",
        emerald: "text-emerald-400 bg-emerald-500/10",
        amber: "text-amber-400 bg-amber-500/10",
        cyan: "text-cyan-400 bg-cyan-500/10",
    };
    return (
        <div className="stat-card">
            <div className="flex items-center gap-2 mb-2">
                <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center ${c[color]}`}
                >
                    <Icon size={14} />
                </div>
                <span className="stat-label">{label}</span>
            </div>
            <div className="stat-value">{value}</div>
            <div className="stat-sub">{sub}</div>
        </div>
    );
}
