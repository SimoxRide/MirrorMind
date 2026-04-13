import { useEffect, useState, type ReactNode } from "react";
import { adminApi, authApi } from "../api/client";
import TipBox from "../components/TipBox";
import {
    Server,
    Database,
    GitBranch,
    Key,
    CheckCircle2,
    XCircle,
    Loader2,
    Save,
    RotateCcw,
} from "lucide-react";

const SERVICE_ICONS: Record<string, ReactNode> = {
    API: <Server className="w-5 h-5" />,
    PostgreSQL: <Database className="w-5 h-5" />,
    Neo4j: <GitBranch className="w-5 h-5" />,
    OpenAI: <Key className="w-5 h-5" />,
};

export default function AdminPage() {
    const [health, setHealth] = useState<Record<string, unknown> | null>(null);
    const [dbHealth, setDbHealth] = useState<Record<string, unknown> | null>(
        null,
    );
    const [neo4jHealth, setNeo4jHealth] = useState<Record<
        string,
        unknown
    > | null>(null);
    const [openaiHealth, setOpenaiHealth] = useState<Record<
        string,
        unknown
    > | null>(null);
    const [providerSettings, setProviderSettings] = useState<{
        has_user_api_key: boolean;
        api_key_source: "user" | "env" | "none";
        effective_api_base: string;
        effective_model: string;
        user_api_base: string | null;
        user_model: string | null;
    } | null>(null);
    const [providerApiKey, setProviderApiKey] = useState("");
    const [providerApiBase, setProviderApiBase] = useState("");
    const [providerModel, setProviderModel] = useState("");
    const [settingsSaving, setSettingsSaving] = useState(false);
    const [settingsMessage, setSettingsMessage] = useState("");
    const [settingsError, setSettingsError] = useState("");

    useEffect(() => {
        adminApi
            .health()
            .then((d) => setHealth(d as unknown as Record<string, unknown>))
            .catch(() => setHealth({ status: "unreachable" }));
        adminApi
            .healthDb()
            .then((d) => setDbHealth(d as unknown as Record<string, unknown>))
            .catch(() => setDbHealth({ postgres: "error" }));
        adminApi
            .healthNeo4j()
            .then((d) =>
                setNeo4jHealth(d as unknown as Record<string, unknown>),
            )
            .catch(() => setNeo4jHealth({ neo4j: "error" }));
        adminApi
            .healthOpenai()
            .then((d) =>
                setOpenaiHealth(d as unknown as Record<string, unknown>),
            )
            .catch(() => setOpenaiHealth({ openai_configured: false }));
        authApi
            .getProviderSettings()
            .then((settings) => {
                setProviderSettings(settings);
                setProviderApiBase(settings.user_api_base ?? "");
                setProviderModel(settings.user_model ?? "");
            })
            .catch(() => setSettingsError("Could not load provider settings."));
    }, []);

    const refreshOpenAIHealth = async () => {
        try {
            const health = await adminApi.healthOpenai();
            setOpenaiHealth(health as unknown as Record<string, unknown>);
        } catch {
            setOpenaiHealth({ openai_configured: false });
        }
    };

    const handleSaveProviderSettings = async () => {
        setSettingsSaving(true);
        setSettingsError("");
        setSettingsMessage("");
        try {
            const payload: {
                api_key?: string;
                api_base?: string;
                model?: string;
            } = {
                api_base: providerApiBase,
                model: providerModel,
            };
            if (providerApiKey.trim()) {
                payload.api_key = providerApiKey;
            }
            const updated = await authApi.updateProviderSettings(payload);
            setProviderSettings(updated);
            setProviderApiKey("");
            setProviderApiBase(updated.user_api_base ?? "");
            setProviderModel(updated.user_model ?? "");
            setSettingsMessage("Provider settings updated.");
            await refreshOpenAIHealth();
        } catch {
            setSettingsError("Could not save provider settings.");
        } finally {
            setSettingsSaving(false);
        }
    };

    const handleClearOverrides = async () => {
        setSettingsSaving(true);
        setSettingsError("");
        setSettingsMessage("");
        try {
            const updated = await authApi.updateProviderSettings({
                api_key: "",
                api_base: "",
                model: "",
            });
            setProviderSettings(updated);
            setProviderApiKey("");
            setProviderApiBase("");
            setProviderModel("");
            setSettingsMessage("Personal provider overrides cleared.");
            await refreshOpenAIHealth();
        } catch {
            setSettingsError("Could not clear provider settings.");
        } finally {
            setSettingsSaving(false);
        }
    };

    return (
        <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-6">
            <h2 className="page-header">Admin / System Health</h2>

            <TipBox
                title="System Health — check everything is running"
                variant="success"
            >
                <ul className="list-disc list-inside space-y-1">
                    <li>
                        <strong>API</strong> — the FastAPI backend
                    </li>
                    <li>
                        <strong>PostgreSQL</strong> — main database (Docker)
                    </li>
                    <li>
                        <strong>Neo4j</strong> — graph database for GraphRAG
                        (Docker)
                    </li>
                    <li>
                        <strong>OpenAI</strong> — API key validation
                    </li>
                </ul>
                <p className="mt-2">
                    If any service shows red, check Docker (
                    <code className="text-slate-300 bg-slate-700/50 px-1.5 py-0.5 rounded text-xs">
                        docker compose up -d
                    </code>
                    ) and your{" "}
                    <code className="text-slate-300 bg-slate-700/50 px-1.5 py-0.5 rounded text-xs">
                        .env
                    </code>{" "}
                    file.
                </p>
            </TipBox>

            <div className="space-y-3">
                <HealthCard title="API" data={health} />
                <HealthCard title="PostgreSQL" data={dbHealth} />
                <HealthCard title="Neo4j" data={neo4jHealth} />
                <HealthCard title="OpenAI" data={openaiHealth} />
            </div>

            <div className="card p-6 space-y-4">
                <div>
                    <h3 className="font-semibold text-white text-base">
                        Provider Settings
                    </h3>
                    <p className="text-sm text-slate-400 mt-1">
                        MirrorMind checks your personal provider settings first.
                        If a field is not set here, it falls back to{" "}
                        <code className="text-slate-300 bg-slate-700/50 px-1.5 py-0.5 rounded text-xs">
                            .env
                        </code>
                        .
                    </p>
                </div>

                {providerSettings && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <StatusPill
                            label="API key source"
                            value={providerSettings.api_key_source}
                        />
                        <StatusPill
                            label="Effective model"
                            value={providerSettings.effective_model}
                        />
                        <StatusPill
                            label="Effective base"
                            value={providerSettings.effective_api_base}
                        />
                    </div>
                )}

                <div className="grid grid-cols-1 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">
                            Personal API key
                        </label>
                        <input
                            type="password"
                            className="input"
                            value={providerApiKey}
                            onChange={(e) => setProviderApiKey(e.target.value)}
                            placeholder={
                                providerSettings?.has_user_api_key
                                    ? "Saved. Enter a new key to replace it, or leave blank."
                                    : "sk-... or provider-compatible key"
                            }
                        />
                        <p className="text-xs text-slate-500 mt-1">
                            Leave blank to keep the current value. Use Clear
                            overrides to remove it and fall back to{" "}
                            <code className="text-slate-300 bg-slate-700/50 px-1 py-0.5 rounded">
                                .env
                            </code>
                            .
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">
                            Personal API base
                        </label>
                        <input
                            type="text"
                            className="input"
                            value={providerApiBase}
                            onChange={(e) =>
                                setProviderApiBase(e.target.value)
                            }
                            placeholder="https://api.openai.com/v1 or compatible base URL"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">
                            Personal model override
                        </label>
                        <input
                            type="text"
                            className="input"
                            value={providerModel}
                            onChange={(e) => setProviderModel(e.target.value)}
                            placeholder="gpt-5.4, gpt-4o, llama-compatible model, ..."
                        />
                    </div>
                </div>

                {settingsMessage && (
                    <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-sm text-emerald-400">
                        {settingsMessage}
                    </div>
                )}
                {settingsError && (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-sm text-red-400">
                        {settingsError}
                    </div>
                )}

                <div className="flex flex-wrap gap-3">
                    <button
                        onClick={handleSaveProviderSettings}
                        disabled={settingsSaving}
                        className="btn-primary"
                    >
                        {settingsSaving ? (
                            "Saving..."
                        ) : (
                            <>
                                <Save className="w-4 h-4" /> Save provider
                                settings
                            </>
                        )}
                    </button>
                    <button
                        onClick={handleClearOverrides}
                        disabled={settingsSaving}
                        className="btn-secondary"
                    >
                        <RotateCcw className="w-4 h-4" /> Clear overrides
                    </button>
                </div>
            </div>
        </div>
    );
}

function StatusPill({ label, value }: { label: string; value: string }) {
    return (
        <div className="bg-slate-900/70 border border-slate-700 rounded-lg p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">
                {label}
            </p>
            <p className="text-sm text-white mt-1 break-all">{value}</p>
        </div>
    );
}

function HealthCard({
    title,
    data,
}: {
    title: string;
    data: Record<string, unknown> | null;
}) {
    const isOk =
        data &&
        (data.status === "ok" ||
            data.postgres === "connected" ||
            data.neo4j === "connected" ||
            data.openai_configured === true);

    return (
        <div className="card-hover p-5 flex items-center justify-between">
            <div className="flex items-center gap-4">
                <div
                    className={`p-2.5 rounded-lg ${data === null ? "bg-slate-700/50 text-slate-500" : isOk ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}
                >
                    {SERVICE_ICONS[title]}
                </div>
                <div>
                    <h3 className="font-medium text-sm text-white">{title}</h3>
                    {data && (
                        <pre className="text-xs text-slate-500 mt-1 font-mono">
                            {JSON.stringify(data, null, 2)}
                        </pre>
                    )}
                </div>
            </div>
            <div>
                {data === null ? (
                    <Loader2 className="w-5 h-5 text-slate-500 animate-spin" />
                ) : isOk ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                ) : (
                    <XCircle className="w-5 h-5 text-red-400" />
                )}
            </div>
        </div>
    );
}
