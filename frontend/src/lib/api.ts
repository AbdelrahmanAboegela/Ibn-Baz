/** API client for communicating with FastAPI backend */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options?.headers,
        },
    });

    if (!res.ok) {
        throw new Error(`API error: ${res.status} ${res.statusText}`);
    }

    return res.json();
}

// ── Fatwas ──
export const api = {
    fatwas: {
        list: (page = 1, perPage = 20, category?: string, search?: string) => {
            const params = new URLSearchParams({
                page: String(page),
                per_page: String(perPage),
            });
            if (category) params.set("category", category);
            if (search) params.set("search", search);
            return fetchApi<any>(`/api/fatwas?${params}`);
        },

        get: (id: number) => fetchApi<any>(`/api/fatwas/${id}`),

        related: (id: number) => fetchApi<any>(`/api/fatwas/${id}/related`),

        categories: () => fetchApi<string[]>("/api/fatwas/categories"),
    },

    // ── Articles ──
    articles: {
        list: (page = 1, perPage = 20) =>
            fetchApi<any>(`/api/articles?page=${page}&per_page=${perPage}`),
        get: (id: number) => fetchApi<any>(`/api/articles/${id}`),
    },

    // ── Books ──
    books: {
        list: () => fetchApi<any[]>("/api/books"),
        get: (id: number) => fetchApi<any>(`/api/books/${id}`),
    },

    // ── Speeches ──
    speeches: {
        list: (page = 1, perPage = 20) =>
            fetchApi<any>(`/api/speeches?page=${page}&per_page=${perPage}`),
        get: (id: number) => fetchApi<any>(`/api/speeches/${id}`),
    },

    // ── Discussions ──
    discussions: {
        list: (page = 1, perPage = 20) =>
            fetchApi<any>(`/api/discussions?page=${page}&per_page=${perPage}`),
        get: (id: number) => fetchApi<any>(`/api/discussions/${id}`),
    },

    // ── Chat ──
    chat: {
        query: (query: string, topK = 5) =>
            fetchApi<any>("/api/chat", {
                method: "POST",
                body: JSON.stringify({ query, top_k: topK }),
            }),

        streamUrl: () => `${API_BASE}/api/chat/stream`,
    },

    // ── Audios ──
    audios: {
        list: (page = 1, perPage = 24) =>
            fetchApi<any>(`/api/audios?page=${page}&per_page=${perPage}`),
        get: (id: number) => fetchApi<any>(`/api/audios/${id}`),
    },

    // ── Stats ──
    stats: () => fetchApi<any>("/api/stats"),

    // ── Audio STT (Fanar-Aura-STT-1 — requires additional Fanar authorization) ──
    audio: {
        transcribe: async (blob: Blob): Promise<{ text: string }> => {
            const form = new FormData();
            form.append("file", blob, "recording.webm");
            const res = await fetch(`${API_BASE}/api/audio/transcribe`, {
                method: "POST",
                body: form,
            });
            if (!res.ok) throw new Error(`STT error: ${res.status}`);
            return res.json();
        },
    },
};

