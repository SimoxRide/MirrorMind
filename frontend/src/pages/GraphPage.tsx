import { useCallback, useEffect, useState } from "react";
import {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    type Node,
    type Edge,
    type EdgeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useAppStore } from "../store/useAppStore";
import { graphApi } from "../api/client";
import type { GraphNode, GraphEdge, RebuildProgress } from "../types";
import TipBox from "../components/TipBox";
import {
    RefreshCw,
    Zap,
    Search,
    X,
    Pencil,
    Trash2,
    Plus,
    Save,
    Link,
    Check,
} from "lucide-react";
import { EDGE_TYPES } from "../graphConstants";

const NODE_COLORS: Record<string, string> = {
    episodic: "#8b5cf6",
    long_term: "#3b82f6",
    decision: "#ef4444",
    preference: "#f59e0b",
    relational: "#ec4899",
    style: "#06b6d4",
    Topic: "#6366f1",
    default: "#475569",
};

const NODE_GLOW: Record<string, string> = {
    episodic: "rgba(139,92,246,.35)",
    long_term: "rgba(59,130,246,.35)",
    decision: "rgba(239,68,68,.35)",
    preference: "rgba(245,158,11,.35)",
    relational: "rgba(236,72,153,.35)",
    style: "rgba(6,182,212,.35)",
    Topic: "rgba(99,102,241,.35)",
    default: "rgba(71,85,105,.25)",
};

export default function GraphPage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
    const [search, setSearch] = useState("");
    const [typeFilter, setTypeFilter] = useState("");
    const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
    const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
    const [loading, setLoading] = useState(false);
    const [rebuilding, setRebuilding] = useState(false);
    const [rebuildProgress, setRebuildProgress] =
        useState<RebuildProgress | null>(null);

    // ── Editing state ───────────────────────────────────
    const [editingNode, setEditingNode] = useState(false);
    const [editNodeLabel, setEditNodeLabel] = useState("");
    const [editNodeType, setEditNodeType] = useState("");
    const [editingEdge, setEditingEdge] = useState(false);
    const [editEdgeType, setEditEdgeType] = useState("");
    const [saving, setSaving] = useState(false);

    // ── "Add Edge" mode ─────────────────────────────────
    const [addEdgeMode, setAddEdgeMode] = useState(false);
    const [addEdgeSource, setAddEdgeSource] = useState<string | null>(null);
    const [newEdgeType, setNewEdgeType] = useState("RELATES_TO");

    // keep a raw edge list for lookups
    const [rawEdges, setRawEdges] = useState<GraphEdge[]>([]);

    const loadGraph = useCallback(async () => {
        if (!activePersonaId) return;
        setLoading(true);
        try {
            const data = await graphApi.query({
                persona_id: activePersonaId,
                query: search || undefined,
                node_type: typeFilter || undefined,
                limit: 200,
            });

            const flowNodes: Node[] = data.nodes.map((n, i) => ({
                id: n.id,
                position: { x: (i % 10) * 200, y: Math.floor(i / 10) * 150 },
                data: { ...n, label: n.label },
                style: {
                    background: `linear-gradient(135deg, ${NODE_COLORS[n.type] || NODE_COLORS.default}dd, ${NODE_COLORS[n.type] || NODE_COLORS.default}99)`,
                    color: "#fff",
                    borderRadius: 12,
                    padding: "10px 16px",
                    fontSize: 12,
                    fontWeight: 500,
                    border: `1px solid ${NODE_COLORS[n.type] || NODE_COLORS.default}`,
                    boxShadow: `0 4px 20px ${NODE_GLOW[n.type] || NODE_GLOW.default}`,
                    backdropFilter: "blur(8px)",
                    letterSpacing: "0.01em",
                },
            }));

            const flowEdges: Edge[] = data.edges.map((e) => ({
                id: e.id,
                source: e.source,
                target: e.target,
                label: e.type,
                animated: true,
                style: { stroke: "#475569", strokeWidth: 1.5 },
                labelStyle: { fontSize: 10, fill: "#94a3b8", fontWeight: 500 },
                labelBgStyle: { fill: "#0f172a", fillOpacity: 0.8 },
                labelBgPadding: [6, 4] as [number, number],
                labelBgBorderRadius: 6,
            }));

            setNodes(flowNodes);
            setEdges(flowEdges);
            setRawEdges(data.edges);
        } finally {
            setLoading(false);
        }
    }, [activePersonaId, search, typeFilter, setNodes, setEdges]);

    useEffect(() => {
        loadGraph();
    }, [loadGraph]);

    const handleNodeClick = (_: React.MouseEvent, node: Node) => {
        if (addEdgeMode) {
            const nodeId = node.id;
            if (!addEdgeSource) {
                setAddEdgeSource(nodeId);
            } else if (nodeId !== addEdgeSource) {
                handleCreateEdge(addEdgeSource, nodeId);
            }
            return;
        }
        setSelectedEdge(null);
        setEditingEdge(false);
        setSelectedNode(node.data as unknown as GraphNode);
        setEditingNode(false);
    };

    const handleEdgeClick: EdgeMouseHandler = (_, edge) => {
        if (addEdgeMode) return;
        setSelectedNode(null);
        setEditingNode(false);
        const raw = rawEdges.find((e) => e.id === edge.id);
        if (raw) {
            setSelectedEdge(raw);
            setEditingEdge(false);
            setEditEdgeType(raw.type);
        }
    };

    // ── Node editing handlers ───────────────────────────
    const startEditNode = () => {
        if (!selectedNode) return;
        setEditNodeLabel(selectedNode.label);
        setEditNodeType(selectedNode.type);
        setEditingNode(true);
    };

    const saveNode = async () => {
        if (!selectedNode) return;
        setSaving(true);
        try {
            const updated = await graphApi.updateNode(selectedNode.id, {
                label: editNodeLabel,
                type: editNodeType,
            });
            setSelectedNode(updated);
            setEditingNode(false);
            await loadGraph();
        } finally {
            setSaving(false);
        }
    };

    const deleteNode = async () => {
        if (!selectedNode) return;
        setSaving(true);
        try {
            await graphApi.deleteNode(selectedNode.id);
            setSelectedNode(null);
            await loadGraph();
        } finally {
            setSaving(false);
        }
    };

    // ── Edge editing handlers ───────────────────────────
    const startEditEdge = () => {
        if (!selectedEdge) return;
        setEditEdgeType(selectedEdge.type);
        setEditingEdge(true);
    };

    const saveEdge = async () => {
        if (!selectedEdge) return;
        setSaving(true);
        try {
            const updated = await graphApi.updateEdge(selectedEdge.id, {
                type: editEdgeType,
            });
            setSelectedEdge(updated);
            setEditingEdge(false);
            await loadGraph();
        } finally {
            setSaving(false);
        }
    };

    const deleteEdge = async () => {
        if (!selectedEdge) return;
        setSaving(true);
        try {
            await graphApi.deleteEdge(selectedEdge.id);
            setSelectedEdge(null);
            await loadGraph();
        } finally {
            setSaving(false);
        }
    };

    // ── Add edge ────────────────────────────────────────
    const handleCreateEdge = async (srcId: string, tgtId: string) => {
        if (!activePersonaId) return;
        setSaving(true);
        try {
            await graphApi.createEdge({
                persona_id: activePersonaId,
                source: srcId,
                target: tgtId,
                type: newEdgeType,
            });
            await loadGraph();
        } finally {
            setSaving(false);
            setAddEdgeMode(false);
            setAddEdgeSource(null);
        }
    };

    const toggleAddEdgeMode = () => {
        setAddEdgeMode(!addEdgeMode);
        setAddEdgeSource(null);
        setSelectedNode(null);
        setSelectedEdge(null);
    };

    const handleRebuild = async () => {
        if (!activePersonaId) return;
        setRebuilding(true);
        setRebuildProgress({
            current: 0,
            total: 0,
            percent: 0,
            current_memory: "Starting...",
            status: "processing",
        });
        try {
            await graphApi.rebuildStream(activePersonaId, (progress) => {
                setRebuildProgress(progress);
            });
            await loadGraph();
        } finally {
            setRebuilding(false);
            setTimeout(() => setRebuildProgress(null), 2000);
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
        <div className="h-full flex flex-col">
            {/* Controls */}
            <div className="p-3 sm:p-4 bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/50 flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                    <h2 className="page-header mr-2 sm:mr-4 text-base sm:text-xl">
                        Knowledge Graph
                    </h2>
                    <div className="relative w-full sm:w-auto order-last sm:order-none mt-1 sm:mt-0">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            className="input pl-9 w-full sm:w-48"
                            placeholder="Search nodes..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && loadGraph()}
                        />
                    </div>
                    <select
                        className="input w-auto"
                        value={typeFilter}
                        onChange={(e) => setTypeFilter(e.target.value)}
                    >
                        <option value="">All types</option>
                        {Object.keys(NODE_COLORS)
                            .filter((k) => k !== "default")
                            .map((t) => (
                                <option key={t} value={t}>
                                    {t}
                                </option>
                            ))}
                    </select>
                    <button onClick={loadGraph} className="btn-secondary">
                        <RefreshCw className="w-4 h-4" /> Refresh
                    </button>
                    <button
                        onClick={handleRebuild}
                        disabled={loading || rebuilding}
                        className="btn-primary"
                    >
                        <Zap className="w-4 h-4" />{" "}
                        {rebuilding ? "Rebuilding..." : "Rebuild Graph"}
                    </button>
                    <button
                        onClick={toggleAddEdgeMode}
                        className={
                            addEdgeMode
                                ? "btn-primary ring-2 ring-green-400"
                                : "btn-secondary"
                        }
                    >
                        <Link className="w-4 h-4" />{" "}
                        {addEdgeMode ? "Cancel" : "Add Edge"}
                    </button>
                    {loading && !rebuilding && (
                        <span className="text-sm text-slate-500 animate-pulse">
                            Loading...
                        </span>
                    )}
                    {saving && (
                        <span className="text-sm text-indigo-400 animate-pulse">
                            Saving...
                        </span>
                    )}
                </div>
                {/* Add Edge info bar */}
                {addEdgeMode && (
                    <div className="flex items-center gap-3 bg-green-900/30 border border-green-700/50 rounded-lg px-4 py-2 text-sm">
                        <span className="text-green-300 font-medium">
                            {!addEdgeSource
                                ? "Click the SOURCE node"
                                : "Now click the TARGET node"}
                        </span>
                        <select
                            className="input w-auto text-xs"
                            value={newEdgeType}
                            onChange={(e) => setNewEdgeType(e.target.value)}
                        >
                            {EDGE_TYPES.map((t) => (
                                <option key={t} value={t}>
                                    {t}
                                </option>
                            ))}
                        </select>
                        {addEdgeSource && (
                            <span className="text-xs text-slate-400">
                                Source:{" "}
                                <code className="text-green-400">
                                    {addEdgeSource.slice(0, 12)}…
                                </code>
                            </span>
                        )}
                    </div>
                )}
                <TipBox
                    title="Knowledge Graph — your clone's relational brain"
                    defaultOpen={false}
                >
                    <p className="mb-2">
                        The graph is <strong>automatically built</strong> from
                        your memories by extracting entities and the
                        relationships between them.
                    </p>
                    <ul className="list-disc list-inside space-y-1">
                        <li>
                            <strong>Rebuild Graph</strong> — re-processes all
                            memories. Do this after adding many new ones
                        </li>
                        <li>
                            <strong>Click any node</strong> to inspect and edit
                            its label, type, or delete it
                        </li>
                        <li>
                            <strong>Click any edge</strong> to edit the
                            relationship type or delete it
                        </li>
                        <li>
                            <strong>Add Edge</strong> — click two nodes to
                            create a new relationship between them
                        </li>
                        <li>
                            <strong>Search + filter</strong> to focus on
                            specific areas of your knowledge network
                        </li>
                    </ul>
                </TipBox>
                {/* Color legend */}
                <div className="flex gap-3 flex-wrap">
                    {Object.entries(NODE_COLORS)
                        .filter(([k]) => k !== "default")
                        .map(([type, color]) => (
                            <div
                                key={type}
                                className="flex items-center gap-1.5 text-xs text-slate-400"
                            >
                                <div
                                    className="w-2.5 h-2.5 rounded-full"
                                    style={{
                                        background: color,
                                        boxShadow: `0 0 6px ${color}80`,
                                    }}
                                />
                                {type.replace("_", " ")}
                            </div>
                        ))}
                </div>
            </div>

            {/* Graph + detail panel */}
            <div className="flex-1 flex relative">
                {/* Rebuild progress overlay */}
                {rebuildProgress && (
                    <div className="absolute inset-0 z-50 bg-slate-950/90 backdrop-blur-sm flex items-center justify-center">
                        <div className="card p-8 max-w-md w-full mx-4">
                            <h3 className="font-bold text-lg mb-4 text-center text-white">
                                {rebuildProgress.status === "done"
                                    ? "Graph Rebuilt!"
                                    : "Rebuilding Knowledge Graph..."}
                            </h3>
                            <div className="w-full bg-slate-700 rounded-full h-2.5 mb-3">
                                <div
                                    className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full h-2.5 transition-all duration-300"
                                    style={{
                                        width: `${rebuildProgress.percent}%`,
                                    }}
                                />
                            </div>
                            <div className="flex justify-between text-sm text-slate-400">
                                <span>
                                    {rebuildProgress.current} /{" "}
                                    {rebuildProgress.total} memories
                                </span>
                                <span>{rebuildProgress.percent}%</span>
                            </div>
                            {rebuildProgress.current_memory &&
                                rebuildProgress.status !== "done" && (
                                    <p className="text-xs text-slate-500 mt-2 truncate text-center">
                                        Processing:{" "}
                                        {rebuildProgress.current_memory}
                                    </p>
                                )}
                        </div>
                    </div>
                )}

                <div className="flex-1" style={{ height: "100%" }}>
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onNodeClick={handleNodeClick}
                        onEdgeClick={handleEdgeClick}
                        fitView
                        proOptions={{ hideAttribution: true }}
                    >
                        <Background color="#1e293b" gap={20} size={1} />
                        <Controls />
                        <MiniMap
                            nodeColor={(n) =>
                                NODE_COLORS[
                                    (n.data as Record<string, string>)?.type
                                ] || NODE_COLORS.default
                            }
                            maskColor="rgba(15, 23, 42, 0.85)"
                        />
                    </ReactFlow>
                </div>

                {/* Detail panel — Node */}
                {selectedNode && (
                    <div
                        className="fixed inset-0 z-50 bg-black/50 lg:static lg:inset-auto lg:z-auto lg:bg-transparent"
                        onClick={() => {
                            setSelectedNode(null);
                            setEditingNode(false);
                        }}
                    >
                        <div
                            className="absolute right-0 top-0 bottom-0 w-[85vw] sm:w-80 bg-slate-900/95 backdrop-blur-sm border-l border-slate-700/50 p-5 overflow-y-auto lg:static lg:w-80"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="font-semibold text-sm text-white">
                                    Node Details
                                </h3>
                                <div className="flex items-center gap-1">
                                    {!editingNode ? (
                                        <>
                                            <button
                                                onClick={startEditNode}
                                                className="p-1 text-slate-400 hover:text-indigo-400 transition-colors"
                                                title="Edit node"
                                            >
                                                <Pencil className="w-3.5 h-3.5" />
                                            </button>
                                            <button
                                                onClick={deleteNode}
                                                className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                                                title="Delete node"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </>
                                    ) : (
                                        <>
                                            <button
                                                onClick={saveNode}
                                                disabled={saving}
                                                className="p-1 text-green-400 hover:text-green-300 transition-colors"
                                                title="Save"
                                            >
                                                <Check className="w-3.5 h-3.5" />
                                            </button>
                                            <button
                                                onClick={() =>
                                                    setEditingNode(false)
                                                }
                                                className="p-1 text-slate-400 hover:text-slate-300 transition-colors"
                                                title="Cancel"
                                            >
                                                <X className="w-3.5 h-3.5" />
                                            </button>
                                        </>
                                    )}
                                    <button
                                        onClick={() => {
                                            setSelectedNode(null);
                                            setEditingNode(false);
                                        }}
                                        className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                            <div className="space-y-3 text-sm">
                                <div>
                                    <span className="text-slate-500 text-xs uppercase tracking-wider">
                                        Label
                                    </span>
                                    {editingNode ? (
                                        <input
                                            className="input mt-1 w-full"
                                            value={editNodeLabel}
                                            onChange={(e) =>
                                                setEditNodeLabel(e.target.value)
                                            }
                                        />
                                    ) : (
                                        <p className="text-white font-medium mt-0.5">
                                            {selectedNode.label}
                                        </p>
                                    )}
                                </div>
                                <div>
                                    <span className="text-slate-500 text-xs uppercase tracking-wider">
                                        Type
                                    </span>
                                    {editingNode ? (
                                        <input
                                            className="input mt-1 w-full"
                                            value={editNodeType}
                                            onChange={(e) =>
                                                setEditNodeType(e.target.value)
                                            }
                                        />
                                    ) : (
                                        <div className="mt-1">
                                            <span className="badge-indigo">
                                                {selectedNode.type}
                                            </span>
                                        </div>
                                    )}
                                </div>
                                <div>
                                    <span className="text-slate-500 text-xs uppercase tracking-wider">
                                        ID
                                    </span>
                                    <p className="font-mono text-xs text-slate-400 mt-0.5 break-all">
                                        {selectedNode.id}
                                    </p>
                                </div>
                                {selectedNode.properties &&
                                    Object.entries(selectedNode.properties).map(
                                        ([k, v]) => (
                                            <div key={k}>
                                                <span className="text-slate-500 text-xs uppercase tracking-wider">
                                                    {k}
                                                </span>
                                                <p className="text-slate-300 mt-0.5 text-sm">
                                                    {typeof v === "object"
                                                        ? JSON.stringify(v)
                                                        : String(v)}
                                                </p>
                                            </div>
                                        ),
                                    )}
                            </div>
                        </div>
                    </div>
                )}

                {/* Detail panel — Edge */}
                {selectedEdge && (
                    <div
                        className="fixed inset-0 z-50 bg-black/50 lg:static lg:inset-auto lg:z-auto lg:bg-transparent"
                        onClick={() => {
                            setSelectedEdge(null);
                            setEditingEdge(false);
                        }}
                    >
                        <div
                            className="absolute right-0 top-0 bottom-0 w-[85vw] sm:w-80 bg-slate-900/95 backdrop-blur-sm border-l border-slate-700/50 p-5 overflow-y-auto lg:static lg:w-80"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="font-semibold text-sm text-white">
                                    Edge Details
                                </h3>
                                <div className="flex items-center gap-1">
                                    {!editingEdge ? (
                                        <>
                                            <button
                                                onClick={startEditEdge}
                                                className="p-1 text-slate-400 hover:text-indigo-400 transition-colors"
                                                title="Edit edge"
                                            >
                                                <Pencil className="w-3.5 h-3.5" />
                                            </button>
                                            <button
                                                onClick={deleteEdge}
                                                className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                                                title="Delete edge"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </>
                                    ) : (
                                        <>
                                            <button
                                                onClick={saveEdge}
                                                disabled={saving}
                                                className="p-1 text-green-400 hover:text-green-300 transition-colors"
                                                title="Save"
                                            >
                                                <Check className="w-3.5 h-3.5" />
                                            </button>
                                            <button
                                                onClick={() =>
                                                    setEditingEdge(false)
                                                }
                                                className="p-1 text-slate-400 hover:text-slate-300 transition-colors"
                                                title="Cancel"
                                            >
                                                <X className="w-3.5 h-3.5" />
                                            </button>
                                        </>
                                    )}
                                    <button
                                        onClick={() => {
                                            setSelectedEdge(null);
                                            setEditingEdge(false);
                                        }}
                                        className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                            <div className="space-y-3 text-sm">
                                <div>
                                    <span className="text-slate-500 text-xs uppercase tracking-wider">
                                        Relationship Type
                                    </span>
                                    {editingEdge ? (
                                        <select
                                            className="input mt-1 w-full"
                                            value={editEdgeType}
                                            onChange={(e) =>
                                                setEditEdgeType(e.target.value)
                                            }
                                        >
                                            {EDGE_TYPES.map((t) => (
                                                <option key={t} value={t}>
                                                    {t}
                                                </option>
                                            ))}
                                            {!EDGE_TYPES.includes(
                                                editEdgeType,
                                            ) && (
                                                <option value={editEdgeType}>
                                                    {editEdgeType}
                                                </option>
                                            )}
                                        </select>
                                    ) : (
                                        <div className="mt-1">
                                            <span className="badge-indigo">
                                                {selectedEdge.type}
                                            </span>
                                        </div>
                                    )}
                                </div>
                                <div>
                                    <span className="text-slate-500 text-xs uppercase tracking-wider">
                                        Source
                                    </span>
                                    <p className="font-mono text-xs text-slate-400 mt-0.5 break-all">
                                        {selectedEdge.source}
                                    </p>
                                </div>
                                <div>
                                    <span className="text-slate-500 text-xs uppercase tracking-wider">
                                        Target
                                    </span>
                                    <p className="font-mono text-xs text-slate-400 mt-0.5 break-all">
                                        {selectedEdge.target}
                                    </p>
                                </div>
                                <div>
                                    <span className="text-slate-500 text-xs uppercase tracking-wider">
                                        ID
                                    </span>
                                    <p className="font-mono text-xs text-slate-400 mt-0.5 break-all">
                                        {selectedEdge.id}
                                    </p>
                                </div>
                                {selectedEdge.properties &&
                                    Object.keys(selectedEdge.properties)
                                        .length > 0 &&
                                    Object.entries(selectedEdge.properties).map(
                                        ([k, v]) => (
                                            <div key={k}>
                                                <span className="text-slate-500 text-xs uppercase tracking-wider">
                                                    {k}
                                                </span>
                                                <p className="text-slate-300 mt-0.5 text-sm">
                                                    {typeof v === "object"
                                                        ? JSON.stringify(v)
                                                        : String(v)}
                                                </p>
                                            </div>
                                        ),
                                    )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
