import { useEffect, useRef, useState } from "react";
import {
    Image as ImageIcon,
    Trash2,
    Sparkles,
    Upload,
    User2,
    Camera,
} from "lucide-react";
import { memoryImageApi, extractErrorMessage } from "../api/client";
import type { MemoryImage, MemoryImageKind } from "../types";

interface Props {
    personaId: string;
    memoryId?: string;
    allowKinds?: MemoryImageKind[];
    defaultKind?: MemoryImageKind;
    title?: string;
    compact?: boolean;
}

const KIND_LABEL: Record<MemoryImageKind, string> = {
    self: "Self",
    memory: "Memory",
    person: "Person",
};

const KIND_BADGE: Record<MemoryImageKind, string> = {
    self: "badge-indigo",
    memory: "badge-purple",
    person: "badge-rose",
};

function Thumbnail({ image }: { image: MemoryImage }) {
    const [url, setUrl] = useState<string | null>(null);
    useEffect(() => {
        let active = true;
        let objectUrl: string | null = null;
        memoryImageApi
            .fetchBlobUrl(image.id)
            .then((u) => {
                if (!active) {
                    URL.revokeObjectURL(u);
                    return;
                }
                objectUrl = u;
                setUrl(u);
            })
            .catch(() => {});
        return () => {
            active = false;
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        };
    }, [image.id]);
    if (!url) {
        return (
            <div className="w-full aspect-square rounded bg-slate-800 flex items-center justify-center">
                <ImageIcon className="w-6 h-6 text-slate-600" />
            </div>
        );
    }
    return (
        <img
            src={url}
            alt={image.title}
            className="w-full aspect-square object-cover rounded"
        />
    );
}

export default function MemoryImageGallery({
    personaId,
    memoryId,
    allowKinds = ["memory", "person", "self"],
    defaultKind = "memory",
    title = "Images",
    compact = false,
}: Props) {
    const [images, setImages] = useState<MemoryImage[]>([]);
    const [kind, setKind] = useState<MemoryImageKind>(defaultKind);
    const [file, setFile] = useState<File | null>(null);
    const [caption, setCaption] = useState("");
    const [uploadTitle, setUploadTitle] = useState("");
    const [tags, setTags] = useState("");
    const [analyze, setAnalyze] = useState(true);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState<string | null>(null);
    const [selected, setSelected] = useState<MemoryImage | null>(null);
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const load = () => {
        if (!personaId) return;
        memoryImageApi
            .list(personaId, {
                limit: 60,
                ...(memoryId ? { memory_id: memoryId } : {}),
            })
            .then(({ items }) => setImages(items))
            .catch((e) => setError(extractErrorMessage(e)));
    };

    useEffect(load, [personaId, memoryId]);

    const handleUpload = async () => {
        if (!file) return;
        setBusy(true);
        setError(null);
        setNotice(null);
        try {
            const res = await memoryImageApi.upload(personaId, file, {
                kind,
                caption: caption || undefined,
                title: uploadTitle || undefined,
                tags: tags || undefined,
                memory_id: memoryId,
                analyze,
            });
            if (res.persona_updated) {
                setNotice("Persona identity updated with new details.");
            } else if (res.image.analysis_status === "ready") {
                setNotice("Image analysed successfully.");
            } else if (res.image.analysis_status === "skipped") {
                setNotice(
                    "Image saved. Analysis skipped (no provider API key configured).",
                );
            } else if (res.image.analysis_status === "failed") {
                setNotice(
                    "Image saved but analysis failed — you can retry from the details view.",
                );
            }
            setFile(null);
            setCaption("");
            setUploadTitle("");
            setTags("");
            load();
        } catch (e) {
            setError(extractErrorMessage(e));
        } finally {
            setBusy(false);
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("Delete this image?")) return;
        await memoryImageApi.delete(id);
        if (selected?.id === id) setSelected(null);
        load();
    };

    const handleReanalyze = async (img: MemoryImage) => {
        setBusy(true);
        setError(null);
        setNotice(null);
        try {
            const res = await memoryImageApi.analyze(
                img.id,
                img.kind === "self",
            );
            setSelected(res.image);
            if (res.persona_updated) {
                setNotice("Persona identity updated with new details.");
            }
            load();
        } catch (e) {
            setError(extractErrorMessage(e));
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <ImageIcon className="w-4 h-4" /> {title}
                </h3>
                <span className="text-xs text-slate-500">
                    {images.length} image{images.length === 1 ? "" : "s"}
                </span>
            </div>

            {/* Upload form */}
            <div className="card p-4 space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                    {allowKinds.map((k) => (
                        <button
                            key={k}
                            onClick={() => setKind(k)}
                            className={
                                kind === k
                                    ? KIND_BADGE[k]
                                    : "badge-slate cursor-pointer hover:bg-slate-600/60"
                            }
                        >
                            {k === "self" && (
                                <User2 className="w-3 h-3 inline mr-1" />
                            )}
                            {KIND_LABEL[k]}
                        </button>
                    ))}
                </div>
                {/* Styled drop zone */}
                <div
                    onDragOver={(e) => {
                        e.preventDefault();
                        setDragOver(true);
                    }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={(e) => {
                        e.preventDefault();
                        setDragOver(false);
                        const dropped = e.dataTransfer.files?.[0];
                        if (dropped && dropped.type.startsWith("image/")) {
                            setFile(dropped);
                        }
                    }}
                    onClick={() => fileInputRef.current?.click()}
                    className={`flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed cursor-pointer transition-colors py-6 px-4 ${
                        dragOver
                            ? "border-indigo-400 bg-indigo-500/10"
                            : file
                              ? "border-emerald-500/60 bg-emerald-500/5"
                              : "border-slate-600 hover:border-slate-400 bg-slate-800/40"
                    }`}
                >
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                        className="hidden"
                    />
                    {file ? (
                        <>
                            <Camera className="w-6 h-6 text-emerald-400" />
                            <span className="text-sm text-emerald-300 font-medium truncate max-w-full">
                                {file.name}
                            </span>
                            <span className="text-xs text-slate-500">
                                {(file.size / 1024).toFixed(0)} KB — click or
                                drop to change
                            </span>
                        </>
                    ) : (
                        <>
                            <Upload className="w-6 h-6 text-slate-400" />
                            <span className="text-sm text-slate-300">
                                Drop an image here or{" "}
                                <span className="text-indigo-400 underline">
                                    browse
                                </span>
                            </span>
                            <span className="text-xs text-slate-500">
                                JPG, PNG, WebP, GIF — max 15 MB
                            </span>
                        </>
                    )}
                </div>
                {!compact && (
                    <>
                        <input
                            className="input"
                            placeholder="Title (optional)"
                            value={uploadTitle}
                            onChange={(e) => setUploadTitle(e.target.value)}
                        />
                        <textarea
                            className="input min-h-[60px]"
                            placeholder="Caption / extra context for analysis"
                            value={caption}
                            onChange={(e) => setCaption(e.target.value)}
                        />
                        <input
                            className="input"
                            placeholder="Tags (comma-separated)"
                            value={tags}
                            onChange={(e) => setTags(e.target.value)}
                        />
                    </>
                )}
                <label className="flex items-center gap-2 text-xs text-slate-400">
                    <input
                        type="checkbox"
                        checked={analyze}
                        onChange={(e) => setAnalyze(e.target.checked)}
                    />
                    Run AI vision analysis on upload
                </label>
                <button
                    onClick={handleUpload}
                    disabled={!file || busy}
                    className="btn-primary disabled:opacity-50"
                >
                    <Upload className="w-4 h-4" />
                    {busy ? "Uploading…" : "Upload image"}
                </button>
            </div>

            {notice && (
                <div className="text-xs text-emerald-400 bg-emerald-500/10 rounded p-2">
                    {notice}
                </div>
            )}
            {error && (
                <div className="text-xs text-red-400 bg-red-500/10 rounded p-2">
                    {error}
                </div>
            )}

            {/* Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {images.map((img) => (
                    <div
                        key={img.id}
                        className="card p-2 space-y-2 cursor-pointer hover:ring-1 hover:ring-indigo-500/40"
                        onClick={() => setSelected(img)}
                    >
                        <Thumbnail image={img} />
                        <div className="flex items-center justify-between">
                            <span
                                className={
                                    KIND_BADGE[img.kind as MemoryImageKind]
                                }
                            >
                                {KIND_LABEL[img.kind as MemoryImageKind] ??
                                    img.kind}
                            </span>
                            <span
                                className={
                                    img.analysis_status === "ready"
                                        ? "badge-emerald"
                                        : img.analysis_status === "failed"
                                          ? "badge-rose"
                                          : "badge-slate"
                                }
                            >
                                {img.analysis_status}
                            </span>
                        </div>
                        <div className="text-xs text-slate-300 truncate">
                            {img.title}
                        </div>
                    </div>
                ))}
                {images.length === 0 && (
                    <div className="col-span-full text-sm text-slate-500 text-center py-8">
                        No images yet.
                    </div>
                )}
            </div>

            {/* Detail modal */}
            {selected && (
                <div
                    className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
                    onClick={() => setSelected(null)}
                >
                    <div
                        className="card max-w-2xl w-full max-h-[90vh] overflow-y-auto p-5 space-y-3"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between">
                            <h4 className="font-semibold">{selected.title}</h4>
                            <button
                                className="text-slate-400 hover:text-white"
                                onClick={() => setSelected(null)}
                            >
                                ✕
                            </button>
                        </div>
                        <Thumbnail image={selected} />
                        {selected.caption && (
                            <p className="text-sm text-slate-300">
                                {selected.caption}
                            </p>
                        )}
                        {selected.tags && selected.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                                {selected.tags.map((t, i) => (
                                    <span key={i} className="badge-cyan">
                                        {t}
                                    </span>
                                ))}
                            </div>
                        )}
                        {selected.analysis &&
                            Object.keys(selected.analysis).length > 0 && (
                                <div className="bg-slate-900/60 rounded p-3">
                                    <div className="text-xs text-slate-500 mb-1">
                                        AI analysis
                                    </div>
                                    <pre className="text-xs text-slate-300 whitespace-pre-wrap break-words">
                                        {JSON.stringify(
                                            selected.analysis,
                                            null,
                                            2,
                                        )}
                                    </pre>
                                </div>
                            )}
                        <div className="flex gap-2">
                            <button
                                onClick={() => handleReanalyze(selected)}
                                disabled={busy}
                                className="btn-secondary"
                            >
                                <Sparkles className="w-4 h-4" />
                                Re-analyse
                                {selected.kind === "self" &&
                                    " & update persona"}
                            </button>
                            <button
                                onClick={() => handleDelete(selected.id)}
                                className="btn-secondary text-red-400"
                            >
                                <Trash2 className="w-4 h-4" />
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
