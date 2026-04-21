import { useEffect, useState } from "react";
import { useAppStore } from "../store/useAppStore";
import { personaApi } from "../api/client";
import type { PersonaCore, PersonaCoreCreate } from "../types";
import TipBox from "../components/TipBox";
import MemoryImageGallery from "../components/MemoryImageGallery";
import { Save, Loader2 } from "lucide-react";

export default function PersonaPage() {
    const activePersonaId = useAppStore((s) => s.activePersonaId);
    const fetchPersonas = useAppStore((s) => s.fetchPersonas);
    const [persona, setPersona] = useState<PersonaCore | null>(null);
    const [saving, setSaving] = useState(false);

    const [name, setName] = useState("");
    const [identity, setIdentity] = useState("");
    const [autonomy, setAutonomy] = useState("medium");
    const [threshold, setThreshold] = useState(0.7);
    const [neverSay, setNeverSay] = useState("");
    const [avoidTopics, setAvoidTopics] = useState("");

    useEffect(() => {
        if (activePersonaId) {
            personaApi.get(activePersonaId).then((p) => {
                setPersona(p);
                setName(p.name);
                setIdentity(p.identity_summary);
                setAutonomy(p.autonomy_level);
                setThreshold(p.confidence_threshold ?? 0.7);
                setNeverSay((p.never_say ?? []).join("\n"));
                setAvoidTopics((p.avoid_topics ?? []).join("\n"));
            });
        } else {
            setPersona(null);
            setName("");
            setIdentity("");
        }
    }, [activePersonaId]);

    const handleSave = async () => {
        setSaving(true);
        try {
            const data = {
                name,
                identity_summary: identity,
                autonomy_level: autonomy,
                confidence_threshold: threshold,
                never_say: neverSay.split("\n").filter(Boolean),
                avoid_topics: avoidTopics.split("\n").filter(Boolean),
            };
            if (persona) {
                await personaApi.update(persona.id, data);
            } else {
                await personaApi.create(data as PersonaCoreCreate);
            }
            await fetchPersonas();
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-6">
            <h2 className="page-header">Persona Core Builder</h2>

            <TipBox title="How to build a great Persona Core">
                <p className="mb-2">
                    The Persona Core is the <strong>foundation</strong> of your
                    clone — everything else builds on it.
                </p>
                <ul className="list-disc list-inside space-y-1">
                    <li>
                        <strong>Name</strong> — display name of your clone
                    </li>
                    <li>
                        <strong>Identity Summary</strong> — write in first
                        person: personality, style, values
                    </li>
                    <li>
                        <strong>Autonomy Level</strong> — Low/Medium/High
                        controls review requirements
                    </li>
                    <li>
                        <strong>Confidence Threshold</strong> — below this,
                        clone flags for review (start with 0.7)
                    </li>
                    <li>
                        <strong>Never Say / Avoid Topics</strong> — hard
                        guardrails, one per line
                    </li>
                </ul>
            </TipBox>

            <div className="card p-6 space-y-5">
                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Name
                    </label>
                    <input
                        type="text"
                        className="input"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Identity Summary
                    </label>
                    <textarea
                        className="input min-h-[120px]"
                        value={identity}
                        onChange={(e) => setIdentity(e.target.value)}
                        placeholder="Describe who you are — your personality, how you communicate, what makes you you..."
                    />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">
                            Autonomy Level
                        </label>
                        <select
                            className="input"
                            value={autonomy}
                            onChange={(e) => setAutonomy(e.target.value)}
                        >
                            <option value="low">
                                Low — always ask before sending
                            </option>
                            <option value="medium">
                                Medium — ask on uncertainty
                            </option>
                            <option value="high">
                                High — send unless policy blocks
                            </option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">
                            Confidence Threshold
                        </label>
                        <input
                            type="number"
                            step={0.1}
                            min={0}
                            max={1}
                            className="input"
                            value={threshold}
                            onChange={(e) =>
                                setThreshold(parseFloat(e.target.value))
                            }
                        />
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Never Say (one per line)
                    </label>
                    <textarea
                        className="input min-h-[80px]"
                        value={neverSay}
                        onChange={(e) => setNeverSay(e.target.value)}
                        placeholder="Things the clone should never say..."
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Avoid Topics (one per line)
                    </label>
                    <textarea
                        className="input min-h-[80px]"
                        value={avoidTopics}
                        onChange={(e) => setAvoidTopics(e.target.value)}
                        placeholder="Topics the clone should avoid..."
                    />
                </div>

                <button
                    onClick={handleSave}
                    disabled={saving || !name}
                    className="btn-primary"
                >
                    {saving ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />{" "}
                            Saving...
                        </>
                    ) : (
                        <>
                            <Save className="w-4 h-4" />{" "}
                            {persona ? "Update Persona" : "Create Persona"}
                        </>
                    )}
                </button>
            </div>

            {persona && (
                <div className="card p-6 space-y-4">
                    <div>
                        <h3 className="text-lg font-semibold">
                            Self-portrait & appearance
                        </h3>
                        <p className="text-sm text-slate-400">
                            Upload a photo of yourself — the clone analyses it
                            and enriches the identity summary automatically with
                            details on appearance, style and mood.
                        </p>
                    </div>
                    <MemoryImageGallery
                        personaId={persona.id}
                        title="Self photos"
                        allowKinds={["self"]}
                        defaultKind="self"
                        compact
                    />
                </div>
            )}
        </div>
    );
}
