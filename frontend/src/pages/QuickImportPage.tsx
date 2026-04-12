import { useState } from "react";
import { useAppStore } from "../store/useAppStore";
import { ioApi } from "../api/client";
import {
    Copy,
    Check,
    Upload,
    Sparkles,
    AlertCircle,
    ChevronDown,
    ChevronUp,
} from "lucide-react";

const CHATGPT_PROMPT = `You are helping me create a structured profile for an AI clone platform called MirrorMind. Based on everything you know about me from our conversations, generate a JSON object with the following structure. Be as detailed and accurate as possible. If you don't have enough information for a field, make a reasonable inference or skip it.

Return ONLY valid JSON, no markdown code fences, no extra text.

{
  "persona": {
    "identity_summary": "A 2-3 sentence summary of who I am — personality, profession, key traits",
    "values": {
      "core_values": ["list of my core values"],
      "priorities": ["what matters most to me"]
    },
    "communication_preferences": {
      "preferred_style": "how I prefer to communicate (direct, diplomatic, casual, formal, etc.)",
      "response_length": "short | medium | detailed",
      "language": "primary language I use"
    },
    "tone": {
      "default": "my usual tone (friendly, professional, sarcastic, warm, etc.)",
      "when_serious": "tone when discussing serious topics",
      "when_casual": "tone in casual conversations"
    },
    "humor_style": {
      "type": "my humor style (dry, witty, self-deprecating, absurd, etc.)",
      "frequency": "how often I use humor (rarely, sometimes, often)"
    },
    "emotional_patterns": {
      "default_mood": "my baseline emotional state",
      "stress_response": "how I handle stress",
      "enthusiasm_triggers": "what excites me"
    },
    "never_say": ["phrases or things I would never say"],
    "avoid_topics": ["topics I prefer to avoid"]
  },
  "memories": [
    {
      "memory_type": "long_term",
      "title": "Short descriptive title",
      "content": "Detailed description of this memory/fact about me",
      "tags": ["relevant", "tags"]
    }
  ],
  "writing_samples": [
    {
      "content": "A message or paragraph written in my typical style",
      "context_type": "general | work | casual | technical",
      "tone": "the tone of this specific sample"
    }
  ],
  "policies": [
    {
      "policy_type": "tone | boundary | privacy | behavior | ethics",
      "name": "Short rule name",
      "description": "Detailed description of this behavioral rule"
    }
  ]
}

Guidelines:
- Include at least 10 memories covering: personal background, professional experience, preferences, relationships, hobbies, skills, opinions, habits
- Include at least 5 writing samples that capture how I actually write in different contexts
- Include at least 5 policies covering: communication boundaries, topics I care about, behavioral rules
- For memory_type use one of: long_term, episodic, relational, preference, project, style, decision
- For policy_type use one of: tone, boundary, privacy, behavior, ethics
- Be specific — generic statements are useless for cloning`;

interface ImportPreview {
    persona: Record<string, unknown> | null;
    memories: Array<Record<string, string | string[]>>;
    writing_samples: Array<Record<string, string>>;
    policies: Array<Record<string, string>>;
}

export default function QuickImportPage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const personas = useAppStore((s) => s.personas);
    const activePersona = personas.find((p) => p.id === activePersonaId);

    const [copied, setCopied] = useState(false);
    const [jsonInput, setJsonInput] = useState("");
    const [preview, setPreview] = useState<ImportPreview | null>(null);
    const [parseError, setParseError] = useState("");
    const [importing, setImporting] = useState(false);
    const [result, setResult] = useState<{
        memories: number;
        writing_samples: number;
        policies: number;
        persona_updated: boolean;
    } | null>(null);
    const [showPrompt, setShowPrompt] = useState(true);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(CHATGPT_PROMPT);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleValidate = () => {
        setParseError("");
        setPreview(null);
        setResult(null);

        const trimmed = jsonInput
            .trim()
            .replace(/^```json?\s*/i, "")
            .replace(/\s*```$/, "");

        try {
            const parsed = JSON.parse(trimmed);
            setPreview({
                persona: parsed.persona || null,
                memories: Array.isArray(parsed.memories) ? parsed.memories : [],
                writing_samples: Array.isArray(parsed.writing_samples)
                    ? parsed.writing_samples
                    : [],
                policies: Array.isArray(parsed.policies) ? parsed.policies : [],
            });
        } catch (e) {
            setParseError(e instanceof Error ? e.message : "Invalid JSON");
        }
    };

    const handleImport = async () => {
        if (!preview || !activePersonaId) return;
        setImporting(true);
        try {
            const trimmed = jsonInput
                .trim()
                .replace(/^```json?\s*/i, "")
                .replace(/\s*```$/, "");
            const res = await ioApi.quickImport(
                activePersonaId,
                JSON.parse(trimmed),
            );
            setResult(res.imported);
            setPreview(null);
            setJsonInput("");
        } catch (e) {
            setParseError("Import failed. Check the console for details.");
        } finally {
            setImporting(false);
        }
    };

    if (!activePersonaId) {
        return (
            <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto">
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-6 text-center">
                    <AlertCircle className="w-8 h-8 text-yellow-400 mx-auto mb-3" />
                    <p className="text-yellow-300">
                        Select a persona from the sidebar to use Quick Import.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-3">
                    <Sparkles className="w-7 h-7 text-purple-400" />
                    Quick Import
                </h1>
                <p className="text-gray-400 mt-2">
                    Use ChatGPT to auto-generate memories, writing samples, and
                    policies for{" "}
                    <span className="text-purple-300 font-medium">
                        {activePersona?.name}
                    </span>
                    .
                </p>
            </div>

            {/* Step 1: Copy prompt */}
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 sm:p-6">
                <button
                    onClick={() => setShowPrompt(!showPrompt)}
                    className="w-full flex items-center justify-between text-left"
                >
                    <h2 className="text-lg font-semibold text-white">
                        Step 1 — Copy the prompt
                    </h2>
                    {showPrompt ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                </button>
                <p className="text-gray-400 text-sm mt-1">
                    Copy this prompt and paste it into{" "}
                    <a
                        href="https://chatgpt.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-purple-400 hover:underline"
                    >
                        ChatGPT
                    </a>{" "}
                    (use a chat where it already knows you well).
                </p>

                {showPrompt && (
                    <div className="mt-4">
                        <pre className="bg-black/40 border border-white/10 rounded-lg p-4 text-xs sm:text-sm text-gray-300 overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap font-mono">
                            {CHATGPT_PROMPT}
                        </pre>
                        <button
                            onClick={handleCopy}
                            className="mt-3 flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium transition-colors"
                        >
                            {copied ? (
                                <>
                                    <Check className="w-4 h-4" /> Copied!
                                </>
                            ) : (
                                <>
                                    <Copy className="w-4 h-4" /> Copy prompt
                                </>
                            )}
                        </button>
                    </div>
                )}
            </div>

            {/* Step 2: Paste JSON */}
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 sm:p-6">
                <h2 className="text-lg font-semibold text-white">
                    Step 2 — Paste the JSON response
                </h2>
                <p className="text-gray-400 text-sm mt-1">
                    Paste the JSON that ChatGPT generated below, then validate
                    it.
                </p>

                <textarea
                    value={jsonInput}
                    onChange={(e) => {
                        setJsonInput(e.target.value);
                        setParseError("");
                        setPreview(null);
                        setResult(null);
                    }}
                    placeholder="Paste the JSON here..."
                    className="mt-4 w-full h-48 sm:h-64 bg-black/40 border border-white/10 rounded-lg p-4 text-sm text-gray-200 font-mono placeholder-gray-600 resize-y focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/30"
                />

                {parseError && (
                    <div className="mt-3 flex items-start gap-2 text-red-400 text-sm">
                        <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                        <span>{parseError}</span>
                    </div>
                )}

                <button
                    onClick={handleValidate}
                    disabled={!jsonInput.trim()}
                    className="mt-3 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
                >
                    Validate JSON
                </button>
            </div>

            {/* Step 3: Preview & Import */}
            {preview && (
                <div className="bg-white/5 border border-white/10 rounded-xl p-4 sm:p-6 space-y-4">
                    <h2 className="text-lg font-semibold text-white">
                        Step 3 — Review & Import
                    </h2>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <PreviewCard
                            label="Memories"
                            count={preview.memories.length}
                            color="blue"
                        />
                        <PreviewCard
                            label="Writing Samples"
                            count={preview.writing_samples.length}
                            color="green"
                        />
                        <PreviewCard
                            label="Policies"
                            count={preview.policies.length}
                            color="orange"
                        />
                    </div>

                    {preview.persona && (
                        <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
                            <p className="text-sm text-purple-300 font-medium mb-1">
                                Persona update included
                            </p>
                            <p className="text-xs text-gray-400">
                                Identity, values, tone, and preferences will be
                                updated.
                            </p>
                        </div>
                    )}

                    {/* Expandable preview lists */}
                    {preview.memories.length > 0 && (
                        <PreviewList
                            title="Memories"
                            items={preview.memories.map(
                                (m) => `[${m.memory_type}] ${m.title}`,
                            )}
                        />
                    )}
                    {preview.writing_samples.length > 0 && (
                        <PreviewList
                            title="Writing Samples"
                            items={preview.writing_samples.map(
                                (s) =>
                                    `[${s.context_type}] ${(s.content || "").slice(0, 80)}...`,
                            )}
                        />
                    )}
                    {preview.policies.length > 0 && (
                        <PreviewList
                            title="Policies"
                            items={preview.policies.map(
                                (p) => `[${p.policy_type}] ${p.name}`,
                            )}
                        />
                    )}

                    <button
                        onClick={handleImport}
                        disabled={importing}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white font-medium transition-colors"
                    >
                        {importing ? (
                            <>
                                <RefreshIcon /> Importing...
                            </>
                        ) : (
                            <>
                                <Upload className="w-5 h-5" /> Import into{" "}
                                {activePersona?.name}
                            </>
                        )}
                    </button>
                </div>
            )}

            {/* Result */}
            {result && (
                <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-6 text-center space-y-2">
                    <Check className="w-10 h-10 text-green-400 mx-auto" />
                    <p className="text-green-300 font-semibold text-lg">
                        Import complete!
                    </p>
                    <p className="text-gray-400 text-sm">
                        {result.memories} memories · {result.writing_samples}{" "}
                        writing samples · {result.policies} policies
                        {result.persona_updated && " · persona updated"}
                    </p>
                </div>
            )}
        </div>
    );
}

function PreviewCard({
    label,
    count,
    color,
}: {
    label: string;
    count: number;
    color: "blue" | "green" | "orange";
}) {
    const colors = {
        blue: "bg-blue-500/10 border-blue-500/20 text-blue-300",
        green: "bg-green-500/10 border-green-500/20 text-green-300",
        orange: "bg-orange-500/10 border-orange-500/20 text-orange-300",
    };
    return (
        <div className={`border rounded-lg p-4 text-center ${colors[color]}`}>
            <p className="text-2xl font-bold">{count}</p>
            <p className="text-sm opacity-80">{label}</p>
        </div>
    );
}

function PreviewList({ title, items }: { title: string; items: string[] }) {
    const [expanded, setExpanded] = useState(false);
    const shown = expanded ? items : items.slice(0, 3);

    return (
        <div className="bg-black/20 rounded-lg p-3">
            <p className="text-sm font-medium text-gray-300 mb-2">{title}</p>
            <ul className="space-y-1">
                {shown.map((item, i) => (
                    <li key={i} className="text-xs text-gray-400 truncate">
                        • {item}
                    </li>
                ))}
            </ul>
            {items.length > 3 && (
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="text-xs text-purple-400 hover:underline mt-2"
                >
                    {expanded ? "Show less" : `Show all ${items.length} items`}
                </button>
            )}
        </div>
    );
}

function RefreshIcon() {
    return (
        <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
            />
            <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
        </svg>
    );
}
