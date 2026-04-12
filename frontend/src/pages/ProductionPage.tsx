import { useEffect, useState } from "react";
import { useAppStore } from "../store/useAppStore";
import { productionApi } from "../api/client";
import type { ProductionClone } from "../types";
import TipBox from "../components/TipBox";
import {
    Rocket,
    Trash2,
    RefreshCw,
    Copy,
    Check,
    Shield,
    Globe,
} from "lucide-react";

export default function ProductionPage() {
    const personas = useAppStore((s) => s.personas);
    const [clones, setClones] = useState<ProductionClone[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedPersona, setSelectedPersona] = useState("");
    const [requireKey, setRequireKey] = useState(true);
    const [copiedId, setCopiedId] = useState<string | null>(null);

    const load = () => {
        setLoading(true);
        productionApi
            .list()
            .then(setClones)
            .finally(() => setLoading(false));
    };

    useEffect(load, []);

    const handleActivate = async () => {
        if (!selectedPersona) return;
        await productionApi.activate(selectedPersona, requireKey);
        setSelectedPersona("");
        load();
    };

    const handleDeactivate = async (id: string) => {
        if (
            !confirm(
                "Deactivate this production clone? The endpoint will stop working.",
            )
        )
            return;
        await productionApi.deactivate(id);
        load();
    };

    const handleRegenerateKey = async (id: string) => {
        if (
            !confirm(
                "Regenerate API key? The old key will stop working immediately.",
            )
        )
            return;
        await productionApi.regenerateKey(id);
        load();
    };

    const copyToClipboard = (text: string, id: string) => {
        navigator.clipboard.writeText(text);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
    };

    const availablePersonas = personas.filter(
        (p) => !clones.some((c) => c.persona_id === p.id),
    );

    return (
        <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
            <h2 className="page-header">Production Clones</h2>

            <TipBox title="Production Clones — deploy your AI clones">
                <p className="mb-2">
                    Once you're satisfied with a clone's quality,{" "}
                    <strong>activate it for production</strong>. Each activated
                    clone gets a unique endpoint you can call from any
                    application.
                </p>
                <ul className="list-disc list-inside space-y-1">
                    <li>
                        <strong>Endpoint</strong> — a REST API endpoint that
                        accepts chat messages and returns clone responses
                    </li>
                    <li>
                        <strong>API Key</strong> — optionally require an API key
                        for authentication
                    </li>
                    <li>
                        <strong>Usage</strong> — integrate with chatbots, apps,
                        or any system that speaks HTTP
                    </li>
                </ul>
                <div className="mt-3 bg-slate-800/60 rounded-lg p-3">
                    <p className="text-xs text-slate-400 font-mono">
                        POST /api/v1/production/chat/{"<endpoint_id>"}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                        Body:{" "}
                        {'{"message": "Hello!", "context_type": "general"}'}
                    </p>
                    <p className="text-xs text-slate-500">
                        Header: X-API-Key: {"<your_api_key>"} (if required)
                    </p>
                </div>
            </TipBox>

            {/* Activate new clone */}
            <div className="card p-5">
                <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                    <Rocket className="w-4 h-4 text-indigo-400" /> Deploy a
                    Clone
                </h3>
                <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
                    <div className="flex-1">
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">
                            Select Persona
                        </label>
                        <select
                            className="input"
                            value={selectedPersona}
                            onChange={(e) => setSelectedPersona(e.target.value)}
                        >
                            <option value="">
                                Choose a persona to deploy...
                            </option>
                            {availablePersonas.map((p) => (
                                <option key={p.id} value={p.id}>
                                    {p.name}
                                </option>
                            ))}
                        </select>
                    </div>
                    <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer sm:pb-2">
                        <input
                            type="checkbox"
                            checked={requireKey}
                            onChange={(e) => setRequireKey(e.target.checked)}
                            className="rounded bg-slate-700 border-slate-600 text-indigo-500 focus:ring-indigo-500/40"
                        />
                        Require API Key
                    </label>
                    <button
                        onClick={handleActivate}
                        disabled={!selectedPersona}
                        className="btn-primary w-full sm:w-auto"
                    >
                        <Rocket className="w-4 h-4" /> Activate
                    </button>
                </div>
            </div>

            {/* Active clones */}
            <div className="space-y-3">
                {clones.map((clone) => (
                    <div key={clone.id} className="card p-5">
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-4">
                            <div className="flex items-center gap-3">
                                <div
                                    className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${clone.is_active ? "bg-emerald-400 shadow-lg shadow-emerald-400/30" : "bg-slate-600"}`}
                                />
                                <div>
                                    <h4 className="text-sm font-semibold text-white">
                                        {clone.persona_name}
                                    </h4>
                                    <span
                                        className={
                                            clone.is_active
                                                ? "badge-emerald"
                                                : "badge-slate"
                                        }
                                    >
                                        {clone.is_active
                                            ? "Active"
                                            : "Inactive"}
                                    </span>
                                </div>
                            </div>
                            <div className="flex items-center gap-2 flex-wrap">
                                {clone.require_api_key ? (
                                    <span className="badge-amber flex items-center gap-1">
                                        <Shield className="w-3 h-3" /> Auth
                                        Required
                                    </span>
                                ) : (
                                    <span className="badge-slate flex items-center gap-1">
                                        <Globe className="w-3 h-3" /> Public
                                    </span>
                                )}
                                <button
                                    onClick={() => handleDeactivate(clone.id)}
                                    className="btn-danger"
                                >
                                    <Trash2 className="w-3.5 h-3.5" /> Remove
                                </button>
                            </div>
                        </div>

                        <div className="space-y-3">
                            {/* Endpoint */}
                            <div>
                                <span className="text-xs text-slate-500 uppercase tracking-wider">
                                    Endpoint
                                </span>
                                <div className="mt-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                                    <code className="flex-1 bg-slate-800/80 rounded-lg px-3 py-2 text-xs text-indigo-400 font-mono overflow-x-auto">
                                        POST /api/v1/production/chat/
                                        {clone.endpoint_id}
                                    </code>
                                    <button
                                        onClick={() =>
                                            copyToClipboard(
                                                `${window.location.origin}/api/v1/production/chat/${clone.endpoint_id}`,
                                                `ep-${clone.id}`,
                                            )
                                        }
                                        className="btn-ghost text-xs"
                                    >
                                        {copiedId === `ep-${clone.id}` ? (
                                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                                        ) : (
                                            <Copy className="w-3.5 h-3.5" />
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* API Key */}
                            {clone.require_api_key && clone.api_key && (
                                <div>
                                    <span className="text-xs text-slate-500 uppercase tracking-wider">
                                        API Key
                                    </span>
                                    <div className="mt-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                                        <code className="flex-1 bg-slate-800/80 rounded-lg px-3 py-2 text-xs text-amber-400 font-mono truncate overflow-x-auto">
                                            {clone.api_key}
                                        </code>
                                        <button
                                            onClick={() =>
                                                copyToClipboard(
                                                    clone.api_key!,
                                                    `key-${clone.id}`,
                                                )
                                            }
                                            className="btn-ghost text-xs"
                                        >
                                            {copiedId === `key-${clone.id}` ? (
                                                <Check className="w-3.5 h-3.5 text-emerald-400" />
                                            ) : (
                                                <Copy className="w-3.5 h-3.5" />
                                            )}
                                        </button>
                                        <button
                                            onClick={() =>
                                                handleRegenerateKey(clone.id)
                                            }
                                            className="btn-ghost text-xs"
                                        >
                                            <RefreshCw className="w-3.5 h-3.5" />{" "}
                                            Regenerate
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {clones.length === 0 && !loading && (
                    <div className="text-center text-slate-500 py-12">
                        No production clones yet. Deploy one above to get
                        started.
                    </div>
                )}
            </div>
        </div>
    );
}
