import { useEffect, useState } from "react";
import { useAppStore } from "../store/useAppStore";
import { extensionApi } from "../api/client";
import type { Extension, ExtensionPlatform } from "../types";
import TipBox from "../components/TipBox";
import {
    Puzzle,
    Plus,
    Trash2,
    Power,
    PowerOff,
    Send,
    MessageCircle,
    Phone,
    Check,
    X,
    Loader2,
    ChevronDown,
} from "lucide-react";

export default function ExtensionsPage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const [extensions, setExtensions] = useState<Extension[]>([]);
    const [platforms, setPlatforms] = useState<ExtensionPlatform[]>([]);
    const [loading, setLoading] = useState(false);
    const [showAdd, setShowAdd] = useState(false);
    const [selectedPlatform, setSelectedPlatform] = useState("");
    const [label, setLabel] = useState("");
    const [credentials, setCredentials] = useState<Record<string, string>>({});
    const [saving, setSaving] = useState(false);
    const [togglingId, setTogglingId] = useState<string | null>(null);

    const ICON_MAP: Record<string, React.ElementType> = {
        Send: Send,
        MessageCircle: MessageCircle,
        Phone: Phone,
    };

    const load = () => {
        if (!activePersonaId) return;
        setLoading(true);
        extensionApi
            .list(activePersonaId)
            .then(setExtensions)
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        extensionApi.platforms().then(setPlatforms);
    }, []);

    useEffect(load, [activePersonaId]);

    const handleCreate = async () => {
        if (!activePersonaId || !selectedPlatform) return;
        setSaving(true);
        try {
            await extensionApi.create({
                persona_id: activePersonaId,
                platform: selectedPlatform,
                label:
                    label ||
                    platforms.find((p) => p.id === selectedPlatform)?.name ||
                    selectedPlatform,
                credentials,
            });
            setShowAdd(false);
            setSelectedPlatform("");
            setLabel("");
            setCredentials({});
            load();
        } finally {
            setSaving(false);
        }
    };

    const handleToggle = async (ext: Extension) => {
        setTogglingId(ext.id);
        try {
            await extensionApi.toggle(ext.id);
            load();
        } finally {
            setTogglingId(null);
        }
    };

    const handleDelete = async (id: string) => {
        if (
            !confirm(
                "Remove this extension? The integration will stop immediately.",
            )
        )
            return;
        await extensionApi.delete(id);
        load();
    };

    const activePlatform = platforms.find((p) => p.id === selectedPlatform);

    if (!activePersonaId) {
        return (
            <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto">
                <h2 className="page-header">Extensions</h2>
                <div className="card p-8 text-center text-slate-400">
                    Select a persona to manage extensions.
                </div>
            </div>
        );
    }

    return (
        <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
            <h2 className="page-header">Extensions</h2>

            <TipBox title="Extensions — connect your clone to external platforms">
                <p className="mb-2">
                    Extend your AI clone beyond the API by connecting it to{" "}
                    <strong>messaging platforms</strong>. Each extension links a
                    persona to an external service.
                </p>
                <ul className="list-disc list-inside space-y-1">
                    <li>
                        <strong>Telegram</strong> — create a bot with{" "}
                        <code className="text-indigo-400">@BotFather</code>,
                        paste the token, and your clone replies automatically
                    </li>
                    <li>
                        <strong>Discord</strong> — create an app at{" "}
                        <code className="text-indigo-400">
                            discord.com/developers
                        </code>
                        , add a bot with MESSAGE CONTENT intent, paste the token
                    </li>
                    <li>
                        <strong>WhatsApp</strong> — set up a WhatsApp Business
                        app via Meta, provide your access token and phone number
                        ID, then configure the webhook URL
                    </li>
                </ul>
            </TipBox>

            {/* Add new extension */}
            <div className="card p-5">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                        <Puzzle className="w-4 h-4 text-indigo-400" />
                        Available Integrations
                    </h3>
                    {!showAdd && (
                        <button
                            onClick={() => setShowAdd(true)}
                            className="btn-primary text-xs"
                        >
                            <Plus className="w-3.5 h-3.5" /> Add Extension
                        </button>
                    )}
                </div>

                {showAdd && (
                    <div className="space-y-4 border border-slate-700 rounded-lg p-4 bg-slate-800/40">
                        {/* Platform selector */}
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1.5">
                                Platform
                            </label>
                            <div className="relative">
                                <select
                                    className="input appearance-none pr-8"
                                    value={selectedPlatform}
                                    onChange={(e) => {
                                        setSelectedPlatform(e.target.value);
                                        setCredentials({});
                                    }}
                                >
                                    <option value="">
                                        Choose a platform...
                                    </option>
                                    {platforms.map((p) => (
                                        <option key={p.id} value={p.id}>
                                            {p.name}
                                        </option>
                                    ))}
                                </select>
                                <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                            </div>
                            {activePlatform && (
                                <p className="text-xs text-slate-500 mt-1">
                                    {activePlatform.description}
                                </p>
                            )}
                        </div>

                        {/* Label */}
                        {activePlatform && (
                            <div>
                                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                                    Label (optional)
                                </label>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder={`My ${activePlatform.name} Bot`}
                                    value={label}
                                    onChange={(e) => setLabel(e.target.value)}
                                />
                            </div>
                        )}

                        {/* Credential fields */}
                        {activePlatform?.credential_fields.map((field) => (
                            <div key={field.key}>
                                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                                    {field.label}
                                </label>
                                <input
                                    type={
                                        field.type === "password"
                                            ? "password"
                                            : "text"
                                    }
                                    className="input font-mono text-xs"
                                    placeholder={field.placeholder}
                                    value={credentials[field.key] || ""}
                                    onChange={(e) =>
                                        setCredentials((prev) => ({
                                            ...prev,
                                            [field.key]: e.target.value,
                                        }))
                                    }
                                />
                                {field.help && (
                                    <p className="text-xs text-slate-500 mt-1">
                                        {field.help}
                                    </p>
                                )}
                            </div>
                        ))}

                        {/* Actions */}
                        <div className="flex gap-2 pt-2">
                            <button
                                onClick={handleCreate}
                                disabled={!selectedPlatform || saving}
                                className="btn-primary text-xs"
                            >
                                {saving ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                    <Check className="w-3.5 h-3.5" />
                                )}
                                Create
                            </button>
                            <button
                                onClick={() => {
                                    setShowAdd(false);
                                    setSelectedPlatform("");
                                    setCredentials({});
                                    setLabel("");
                                }}
                                className="btn-ghost text-xs"
                            >
                                <X className="w-3.5 h-3.5" /> Cancel
                            </button>
                        </div>
                    </div>
                )}

                {/* Platform cards if nothing to add */}
                {!showAdd && platforms.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {platforms.map((p) => {
                            const Icon = ICON_MAP[p.icon] || Puzzle;
                            const count = extensions.filter(
                                (e) => e.platform === p.id,
                            ).length;
                            return (
                                <div
                                    key={p.id}
                                    className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4 flex items-start gap-3"
                                >
                                    <div className="w-9 h-9 rounded-lg bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
                                        <Icon className="w-4.5 h-4.5 text-indigo-400" />
                                    </div>
                                    <div className="min-w-0">
                                        <h4 className="text-sm font-medium text-white">
                                            {p.name}
                                        </h4>
                                        <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">
                                            {p.description}
                                        </p>
                                        {count > 0 && (
                                            <span className="badge-indigo mt-1.5 inline-block text-[10px]">
                                                {count} active
                                            </span>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Existing extensions */}
            {loading ? (
                <div className="card p-8 text-center text-slate-400 flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Loading
                    extensions...
                </div>
            ) : extensions.length === 0 ? (
                <div className="card p-8 text-center text-slate-500 text-sm">
                    No extensions configured yet. Click "Add Extension" above to
                    connect your clone to Telegram or other platforms.
                </div>
            ) : (
                <div className="space-y-3">
                    {extensions.map((ext) => {
                        const platform = platforms.find(
                            (p) => p.id === ext.platform,
                        );
                        const Icon = ICON_MAP[platform?.icon || ""] || Puzzle;
                        return (
                            <div key={ext.id} className="card p-5">
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                                    <div className="flex items-center gap-3">
                                        <div
                                            className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                                                ext.is_active && ext.bot_running
                                                    ? "bg-emerald-400 shadow-lg shadow-emerald-400/30"
                                                    : ext.is_active
                                                      ? "bg-amber-400"
                                                      : "bg-slate-600"
                                            }`}
                                        />
                                        <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
                                            <Icon className="w-4 h-4 text-indigo-400" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-semibold text-white">
                                                {ext.label ||
                                                    platform?.name ||
                                                    ext.platform}
                                            </h4>
                                            <div className="flex items-center gap-2 mt-0.5">
                                                <span className="text-xs text-slate-500 capitalize">
                                                    {ext.platform}
                                                </span>
                                                {ext.is_active &&
                                                    ext.bot_running && (
                                                        <span className="badge-emerald text-[10px]">
                                                            Running
                                                        </span>
                                                    )}
                                                {ext.is_active &&
                                                    !ext.bot_running && (
                                                        <span className="badge-amber text-[10px]">
                                                            Starting...
                                                        </span>
                                                    )}
                                                {!ext.is_active && (
                                                    <span className="badge-slate text-[10px]">
                                                        Disabled
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => handleToggle(ext)}
                                            disabled={togglingId === ext.id}
                                            className={
                                                ext.is_active
                                                    ? "btn-ghost text-xs text-amber-400 hover:text-amber-300"
                                                    : "btn-ghost text-xs text-emerald-400 hover:text-emerald-300"
                                            }
                                        >
                                            {togglingId === ext.id ? (
                                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                            ) : ext.is_active ? (
                                                <PowerOff className="w-3.5 h-3.5" />
                                            ) : (
                                                <Power className="w-3.5 h-3.5" />
                                            )}
                                            {ext.is_active
                                                ? "Disable"
                                                : "Enable"}
                                        </button>
                                        <button
                                            onClick={() => handleDelete(ext.id)}
                                            className="btn-danger text-xs"
                                        >
                                            <Trash2 className="w-3.5 h-3.5" />{" "}
                                            Remove
                                        </button>
                                    </div>
                                </div>

                                {/* Details */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                                    {ext.credentials &&
                                        Object.entries(ext.credentials).map(
                                            ([key, val]) => (
                                                <div key={key}>
                                                    <span className="text-slate-500 uppercase tracking-wider">
                                                        {key.replace(/_/g, " ")}
                                                    </span>
                                                    <div className="mt-0.5 bg-slate-800/80 rounded px-2.5 py-1.5 text-slate-400 font-mono truncate">
                                                        {val}
                                                    </div>
                                                </div>
                                            ),
                                        )}
                                    <div>
                                        <span className="text-slate-500 uppercase tracking-wider">
                                            Created
                                        </span>
                                        <div className="mt-0.5 text-slate-400">
                                            {new Date(
                                                ext.created_at,
                                            ).toLocaleDateString()}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
