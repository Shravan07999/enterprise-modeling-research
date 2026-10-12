import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
});

export const PromptService = {
    getAll: async () => {
        const response = await api.get('/prompts/');
        return response.data;
    },
    getById: async (id: number) => {
        const response = await api.get(`/prompts/${id}`);
        return response.data;
    },
    create: async (data: any) => {
        const response = await api.post('/prompts/', data);
        return response.data;
    },
    delete: async (id: number) => {
        const response = await api.delete(`/prompts/${id}`);
        return response.data;
    },
};

export const ChainService = {
    getAll: async () => {
        const response = await api.get('/chains/');
        return response.data;
    },
    create: async (data: any) => {
        const response = await api.post('/chains/', data);
        return response.data;
    },
    addStep: async (chainId: number, stepData: any) => {
        const response = await api.post(`/chains/${chainId}/steps`, stepData);
        return response.data;
    },
    update: async (id: number, data: any) => {
        const response = await api.patch(`/chains/${id}`, data);
        return response.data;
    },
    delete: async (id: number) => {
        const response = await api.delete(`/chains/${id}`);
        return response.data;
    },
};

export const AnalyticsService = {
    getUsage: async () => {
        const response = await api.get('/analytics/usage');
        return response.data;
    },
    getAuditLogs: async () => {
        const response = await api.get('/analytics/history');
        return response.data;
    },
};

export const ExecutionService = {
    execute: async (promptId: number, inputs: Record<string, any>) => {
        const response = await api.post('/execute/', {
            prompt_id: promptId,
            inputs: inputs,
        });
        return response.data;
    },
    executeChain: async (chainId: number, inputs: Record<string, any>) => {
        const response = await api.post('/execute/chain', {
            chain_id: chainId,
            inputs: inputs,
        });
        return response.data;
    },
    getHistory: async () => {
        const response = await api.get('/execute/history');
        return response.data;
    },
};

// --- Pipeline telemetry (per-stage latency + token usage) ---

export interface StepMetrics {
    step: number;
    prompt_name: string;
    type: string;
    model?: string | null;
    latency_seconds: number;
    prompt_tokens: number; // -1 = unavailable (simulation fallback)
    completion_tokens: number; // -1 = unavailable (simulation fallback)
}

export interface MetricsTotals {
    total_latency_seconds: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
}

// Chain executions return { steps, totals }; single-prompt executions return a flat shape.
export interface ExecutionMetrics {
    steps?: StepMetrics[];
    totals?: MetricsTotals;
    latency_seconds?: number;
    prompt_tokens?: number;
    completion_tokens?: number;
    model?: string | null;
}

export interface ExportStepPayload {
    step: number;
    prompt_name: string;
    type: string;
    result: string;
}

export interface ExportPayload {
    chain_name: string;
    steps: ExportStepPayload[];
    history_id?: number;
    inputs?: Record<string, any>;
}

export interface ExportFile {
    blob: Blob;
    filename: string;
}

const extractFilename = (contentDisposition: string | undefined, fallback: string): string => {
    if (!contentDisposition) return fallback;
    const match = contentDisposition.match(/filename="?([^";]+)"?/);
    return match ? match[1] : fallback;
};

const slugFromName = (name: string): string =>
    (name || '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'export';

const postExportFile = async (url: string, data: ExportPayload, fallback: string): Promise<ExportFile> => {
    try {
        const response = await api.post(url, data, { responseType: 'blob' });
        const filename = extractFilename(
            response.headers['content-disposition'] as string | undefined,
            'export.adl'
        );
        return { blob: response.data as Blob, filename };
    } catch (error: any) {
        // FastAPI returns JSON errors; with responseType 'blob' they arrive as a Blob
        if (error.response?.data instanceof Blob) {
            const text = await error.response.data.text();
            let detail = text;
            try {
                const parsed = JSON.parse(text);
                detail = parsed.detail || text;
            } catch {
                // not JSON, keep raw text
            }
            throw new Error(detail || 'Export failed');
        }
        throw error;
    }
};

export const ExportService = {
    exportAdl: (payload: ExportPayload): Promise<ExportFile> =>
        postExportFile('/export/adl', payload, `${slugFromName(payload.chain_name)}-4EM-General-Model.adl`),
    exportArchimate: (payload: ExportPayload): Promise<ExportFile> =>
        postExportFile('/export/archimate', payload, `${slugFromName(payload.chain_name)}.archimate`),
};

export const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
};

export default api;
