import { useEffect, useState } from "react";
import { adminApi } from "../api/client";
import TipBox from "../components/TipBox";
import {
    Server,
    Database,
    GitBranch,
    Key,
    CheckCircle2,
    XCircle,
    Loader2,
} from "lucide-react";

const SERVICE_ICONS: Record<string, React.ReactNode> = {
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
    }, []);

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
