import axios from "axios";
import type {
    PersonaCore,
    PersonaCoreCreate,
    Memory,
    MemoryCreate,
    WritingSample,
    PolicyRule,
    TestScenario,
    CloneRequest,
    CloneResponse,
    ImprovementSuggestion,
    ApplyFixResponse,
    GraphNode,
    GraphEdge,
    GraphSubgraph,
    Evaluation,
    HealthStatus,
    TrainingQuestion,
    AnalysisResult,
    RebuildProgress,
    AuthToken,
    SetupStatus,
    ProductionClone,
    DocumentAnalysis,
    QuickImportResult,
    ProviderSettings,
} from "../types";

const api = axios.create({
    baseURL: "/api/v1",
});

// ── Auth interceptor ────────────────────────────────────
api.interceptors.request.use((config) => {
    const token = localStorage.getItem("mm_token");
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    (res) => res,
    (err) => {
        if (
            err.response?.status === 401 &&
            !err.config?.url?.includes("/auth/")
        ) {
            localStorage.removeItem("mm_token");
            localStorage.removeItem("mm_user");
            window.location.href = "/login";
        }
        return Promise.reject(err);
    },
);

// ── Auth ────────────────────────────────────────────────

export const authApi = {
    setupStatus: () =>
        api.get<SetupStatus>("/auth/setup-status").then((r) => r.data),
    setup: (data: { email: string; password: string }) =>
        api.post<AuthToken>("/auth/setup", data).then((r) => r.data),
    register: (data: { email: string; password: string }) =>
        api.post<AuthToken>("/auth/register", data).then((r) => r.data),
    login: (data: { email: string; password: string }) =>
        api.post<AuthToken>("/auth/login", data).then((r) => r.data),
    getProviderSettings: () =>
        api
            .get<ProviderSettings>("/auth/provider-settings")
            .then((r) => r.data),
    updateProviderSettings: (data: {
        api_key?: string;
        api_base?: string;
        model?: string;
    }) =>
        api
            .patch<ProviderSettings>("/auth/provider-settings", data)
            .then((r) => r.data),
};

// ── Persona ─────────────────────────────────────────────

export const personaApi = {
    list: () => api.get<PersonaCore[]>("/personas/").then((r) => r.data),
    get: (id: string) =>
        api.get<PersonaCore>(`/personas/${id}`).then((r) => r.data),
    create: (data: PersonaCoreCreate) =>
        api.post<PersonaCore>("/personas/", data).then((r) => r.data),
    update: (id: string, data: Partial<PersonaCoreCreate>) =>
        api.patch<PersonaCore>(`/personas/${id}`, data).then((r) => r.data),
    delete: (id: string) => api.delete(`/personas/${id}`),
};

export interface Paginated<T> {
    items: T[];
    total: number;
}

// ── Memory ──────────────────────────────────────────────

export const memoryApi = {
    list: (
        personaId: string,
        params?: {
            memory_type?: string;
            limit?: number;
            offset?: number;
        },
    ): Promise<Paginated<Memory>> =>
        api
            .get<Memory[]>("/memories/", {
                params: { persona_id: personaId, ...params },
            })
            .then((r) => ({
                items: r.data,
                total: parseInt(r.headers["x-total-count"] || "0", 10),
            })),
    get: (id: string) => api.get<Memory>(`/memories/${id}`).then((r) => r.data),
    create: (data: MemoryCreate) =>
        api.post<Memory>("/memories/", data).then((r) => r.data),
    update: (id: string, data: Partial<Memory>) =>
        api.patch<Memory>(`/memories/${id}`, data).then((r) => r.data),
    delete: (id: string) => api.delete(`/memories/${id}`),
};

// ── Writing Samples ─────────────────────────────────────

export const writingSampleApi = {
    list: (
        personaId: string,
        params?: {
            context_type?: string;
            limit?: number;
            offset?: number;
        },
    ): Promise<Paginated<WritingSample>> =>
        api
            .get<WritingSample[]>("/writing-samples/", {
                params: { persona_id: personaId, ...params },
            })
            .then((r) => ({
                items: r.data,
                total: parseInt(r.headers["x-total-count"] || "0", 10),
            })),
    create: (
        data: Partial<WritingSample> & { persona_id: string; content: string },
    ) => api.post<WritingSample>("/writing-samples/", data).then((r) => r.data),
    update: (id: string, data: Partial<WritingSample>) =>
        api
            .patch<WritingSample>(`/writing-samples/${id}`, data)
            .then((r) => r.data),
    delete: (id: string) => api.delete(`/writing-samples/${id}`),
};

// ── Policies ────────────────────────────────────────────

export const policyApi = {
    list: (
        personaId: string,
        params?: {
            policy_type?: string;
            limit?: number;
            offset?: number;
        },
    ): Promise<Paginated<PolicyRule>> =>
        api
            .get<PolicyRule[]>("/policies/", {
                params: { persona_id: personaId, ...params },
            })
            .then((r) => ({
                items: r.data,
                total: parseInt(r.headers["x-total-count"] || "0", 10),
            })),
    create: (
        data: Partial<PolicyRule> & {
            persona_id: string;
            policy_type: string;
            name: string;
        },
    ) => api.post<PolicyRule>("/policies/", data).then((r) => r.data),
    update: (id: string, data: Partial<PolicyRule>) =>
        api.patch<PolicyRule>(`/policies/${id}`, data).then((r) => r.data),
    delete: (id: string) => api.delete(`/policies/${id}`),
};

// ── Testing ─────────────────────────────────────────────

export const testingApi = {
    listScenarios: (personaId: string) =>
        api
            .get<
                TestScenario[]
            >("/testing/scenarios", { params: { persona_id: personaId } })
            .then((r) => r.data),
    createScenario: (
        data: Partial<TestScenario> & {
            persona_id: string;
            title: string;
            input_message: string;
        },
    ) => api.post<TestScenario>("/testing/scenarios", data).then((r) => r.data),
    runClone: (data: CloneRequest) =>
        api.post<CloneResponse>("/testing/run", data).then((r) => r.data),
    createEvaluation: (
        data: Partial<Evaluation> & { test_result_id: string },
    ) => api.post<Evaluation>("/testing/evaluations", data).then((r) => r.data),
    applyFix: (personaId: string, suggestion: ImprovementSuggestion) =>
        api
            .post<ApplyFixResponse>("/testing/apply-fix", {
                persona_id: personaId,
                suggestion,
            })
            .then((r) => r.data),
};

// ── Graph ───────────────────────────────────────────────

export const graphApi = {
    query: (data: {
        persona_id: string;
        query?: string;
        node_type?: string;
        depth?: number;
        limit?: number;
    }) => api.post<GraphSubgraph>("/graph/query", data).then((r) => r.data),
    ingestMemory: (personaId: string, memoryId: string) =>
        api
            .post("/graph/ingest/memory", null, {
                params: { persona_id: personaId, memory_id: memoryId },
            })
            .then((r) => r.data),
    rebuild: (personaId: string) =>
        api
            .post("/graph/rebuild", null, { params: { persona_id: personaId } })
            .then((r) => r.data),
    rebuildStream: (
        personaId: string,
        onProgress: (data: RebuildProgress) => void,
    ) => {
        return fetch(`/api/v1/graph/rebuild?persona_id=${personaId}`, {
            method: "POST",
        }).then(async (response) => {
            const reader = response.body?.getReader();
            if (!reader) return;
            const decoder = new TextDecoder();
            let buffer = "";
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";
                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            onProgress(data);
                        } catch {
                            /* ignore parse errors */
                        }
                    }
                }
            }
        });
    },
    // ── Node CRUD ──
    updateNode: (
        nodeId: string,
        data: {
            label?: string;
            type?: string;
            properties?: Record<string, unknown>;
        },
    ) =>
        api
            .patch<GraphNode>(`/graph/nodes/${nodeId}`, data)
            .then((r) => r.data),
    deleteNode: (nodeId: string) =>
        api.delete(`/graph/nodes/${nodeId}`).then((r) => r.data),
    // ── Edge CRUD ──
    createEdge: (data: {
        persona_id: string;
        source: string;
        target: string;
        type: string;
        properties?: Record<string, unknown>;
    }) => api.post<GraphEdge>(`/graph/edges`, data).then((r) => r.data),
    updateEdge: (
        edgeId: string,
        data: { type?: string; properties?: Record<string, unknown> },
    ) =>
        api
            .patch<GraphEdge>(
                `/graph/edges/${encodeURIComponent(edgeId)}`,
                data,
            )
            .then((r) => r.data),
    deleteEdge: (edgeId: string) =>
        api
            .delete(`/graph/edges/${encodeURIComponent(edgeId)}`)
            .then((r) => r.data),
};

// ── Admin ───────────────────────────────────────────────

export const adminApi = {
    health: () => api.get<HealthStatus>("/admin/health").then((r) => r.data),
    healthDb: () => api.get("/admin/health/db").then((r) => r.data),
    healthNeo4j: () => api.get("/admin/health/neo4j").then((r) => r.data),
    healthOpenai: () => api.get("/admin/health/openai").then((r) => r.data),
};

// ── Training Lab ────────────────────────────────────────

export const trainingApi = {
    generateQuestions: (data: {
        persona_id: string;
        count?: number;
        categories?: string[];
        previous_questions?: string[];
    }) =>
        api
            .post<TrainingQuestion[]>("/training/generate-questions", data)
            .then((r) => r.data),
    analyzeAnswer: (data: {
        persona_id: string;
        question: string;
        category: string;
        context_type: string;
        answer: string;
        auto_save?: boolean;
    }) =>
        api
            .post<AnalysisResult>("/training/analyze-answer", data)
            .then((r) => r.data),
};

// ── Import/Export ───────────────────────────────────────

export const ioApi = {
    exportPersona: (personaId: string) =>
        api.get(`/io/export/persona/${personaId}`).then((r) => r.data),
    importPersona: (bundle: Record<string, unknown>) =>
        api.post("/io/import/persona", bundle).then((r) => r.data),
    analyzeDocument: (
        personaId: string,
        file: File,
        options?: { sourceKind?: string; notes?: string },
    ) => {
        const formData = new FormData();
        formData.append("persona_id", personaId);
        formData.append("file", file);
        if (options?.sourceKind) {
            formData.append("source_kind", options.sourceKind);
        }
        if (options?.notes) {
            formData.append("notes", options.notes);
        }
        return api
            .post<DocumentAnalysis>("/io/analyze-document", formData)
            .then((r) => r.data);
    },
    quickImport: (
        personaId: string,
        data: Record<string, unknown>,
        sourceLabel?: string,
    ) =>
        api
            .post<{ imported: QuickImportResult }>("/io/quick-import", {
                persona_id: personaId,
                data,
                source_label: sourceLabel,
            })
            .then((r) => r.data),
};

// ── Production Clones ──────────────────────────────────

export const productionApi = {
    list: () =>
        api.get<ProductionClone[]>("/production/clones").then((r) => r.data),
    activate: (personaId: string, requireApiKey: boolean) =>
        api
            .post<ProductionClone>("/production/clones", {
                persona_id: personaId,
                require_api_key: requireApiKey,
            })
            .then((r) => r.data),
    deactivate: (id: string) => api.delete(`/production/clones/${id}`),
    regenerateKey: (id: string) =>
        api
            .post<ProductionClone>(`/production/clones/${id}/regenerate-key`)
            .then((r) => r.data),
};
