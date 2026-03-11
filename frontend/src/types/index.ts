/** TypeScript types matching the FastAPI backend models */

export interface QuranCitation {
    reference: string;
    surah_number: number;
    ayah_number: number;
    surah_name: string;
    verified_text: string;
    quran_url: string;
}

export interface HadithCitation {
    text: string;
    collection: string;
    collector: string;
    sunnah_url: string;
    // Enriched from dorar.net (primary source):
    verified_text?: string;
    narrator?: string;
    grade?: string;
    grade_level?: number;  // 1=sahih, 2=hasan, 3=daif, 4=mawdu
    source_book?: string;
    dorar_url?: string;
    // Cross-reference from sunnah.com (secondary source, optional):
    sunnah_grade?: string;
    sunnah_text_en?: string;
    // Additional reference links:
    islamweb_url?: string;
}

export interface FatwaBrief {
    fatwa_id: number;
    title: string;
    question: string;
    answer_preview: string;
    categories: string[];
    source_ref: string;
    has_audio: boolean;
}

export interface FatwaFull {
    fatwa_id: number;
    title: string;
    question: string;
    answer: string;
    answer_direct: string;
    source_ref: string;
    url: string;
    categories: string[];
    related_ids: number[];
    audio_url: string;
    quran_citations: QuranCitation[];
    hadith_citations: HadithCitation[];
}

export interface RelatedFatwa {
    fatwa_id: number;
    title: string;
}

export interface ArticleBrief {
    id: number;
    title: string;
    text_preview: string;
    categories: string[];
    date: string;
    source_ref: string;
}

export interface BookItem {
    id: number;
    title: string;
    url: string;
    pdf_url: string;
}

export interface SpeechBrief {
    id: number;
    title: string;
    text_preview: string;
    categories: string[];
    date: string;
}

export interface DiscussionBrief {
    id: number;
    title: string;
    text_preview: string;
    categories: string[];
}

export interface CitedFatwa {
    fatwa_id: number;
    title: string;
    source_ref: string;
    url: string;
    relevance_score: number;
}

export interface ChatResponse {
    answer: string;
    confidence: number;
    cited_fatwas: CitedFatwa[];
    quran_citations: QuranCitation[];
    hadith_citations: HadithCitation[];
    related_fatwas: RelatedFatwa[];
    query_time_ms: number;
}

export interface DashboardStats {
    total_fatwas: number;
    total_articles: number;
    total_books: number;
    total_speeches: number;
    total_discussions: number;
    total_categories: number;
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
}

// SSE streaming types
export interface SSEEvent {
    type: "status" | "chunk" | "metadata" | "done" | "error";
    content?: string | ChatResponse;
}
