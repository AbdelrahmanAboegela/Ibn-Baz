"""
Pydantic models for the BinBaz RAG API.
Shared between routes, pipeline, and generator.
"""
from pydantic import BaseModel, Field
from typing import Optional


# ──────────────────────────────── Fatwa ────────────────────────────────

class QuranCitation(BaseModel):
    reference: str = ""                  # e.g. "البقرة:173"
    surah_number: int = 0
    ayah_number: int = 0
    surah_name: str = ""
    verified_text: str = ""
    quran_url: str = ""


class HadithCitation(BaseModel):
    text: str = ""                       # extracted hadith body snippet (used for dorar search)
    collection: str = ""                 # Arabic collection name, e.g. "البخاري"
    collector: str = ""                  # display name, e.g. "الإمام البخاري"
    sunnah_url: str = ""                 # deep link to sunnah.com collection
    # Verified via dorar.net (primary source):
    verified_text: str = ""              # clean hadith text from dorar database
    narrator: str = ""                   # رواي (companion who narrated)
    grade: str = ""                      # e.g. "صحيح", "حسن", "ضعيف"
    grade_level: int = 0                 # 1=sahih, 2=hasan, 3=daif, 4=mawdu/very weak
    source_book: str = ""                # specific book, e.g. "صحيح أبي داود"
    dorar_url: str = ""                  # direct search link on dorar.net
    # Cross-reference from sunnah.com (secondary source, populated when API key is set):
    sunnah_grade: str = ""               # grade from sunnah.com scholars
    sunnah_text_en: str = ""             # English translation from sunnah.com
    # Additional reference links:
    islamweb_url: str = ""               # islamweb.net search link


class FatwaBrief(BaseModel):
    """Compact fatwa for list views."""
    fatwa_id: int
    title: str
    question: str = ""
    answer_preview: str = ""             # first 300 chars
    categories: list[str] = []
    source_ref: str = ""
    has_audio: bool = False


class FatwaFull(BaseModel):
    """Complete fatwa for detail view."""
    fatwa_id: int
    title: str
    question: str = ""
    answer: str = ""
    answer_direct: str = ""
    source_ref: str = ""
    url: str = ""
    categories: list[str] = []
    related_ids: list[int] = []
    audio_url: str = ""
    quran_citations: list[QuranCitation] = []
    hadith_citations: list[HadithCitation] = []


class RelatedFatwa(BaseModel):
    fatwa_id: int
    title: str


# ──────────────────────────────── Content ────────────────────────────────

class ArticleBrief(BaseModel):
    id: int
    title: str
    text_preview: str = ""
    categories: list[str] = []
    date: str = ""
    source_ref: str = ""


class BookItem(BaseModel):
    id: int
    title: str
    url: str = ""
    pdf_url: str = ""


class SpeechBrief(BaseModel):
    id: int
    title: str
    text_preview: str = ""
    categories: list[str] = []
    date: str = ""


class DiscussionBrief(BaseModel):
    id: int
    title: str
    text_preview: str = ""
    categories: list[str] = []


# ──────────────────────────────── Chat / RAG ────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class CitedFatwa(BaseModel):
    fatwa_id: int
    title: str
    source_ref: str = ""
    url: str = ""
    relevance_score: float = 0.0


class RAGResponse(BaseModel):
    """Structured LLM output — validated by PydanticAI."""
    answer: str                          # Arabic generated answer
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    cited_fatwa_ids: list[int] = []      # IDs mentioned in answer
    cited_quran_refs: list[str] = []     # e.g. ["البقرة:173"]


class ChatResponse(BaseModel):
    """Full response sent to frontend."""
    answer: str
    confidence: float = 0.0
    cited_fatwas: list[CitedFatwa] = []
    quran_citations: list[QuranCitation] = []
    hadith_citations: list[HadithCitation] = []
    related_fatwas: list[RelatedFatwa] = []
    query_time_ms: float = 0.0


# ──────────────────────────────── Stats ────────────────────────────────

class DashboardStats(BaseModel):
    total_fatwas: int = 0
    total_articles: int = 0
    total_books: int = 0
    total_speeches: int = 0
    total_discussions: int = 0
    total_categories: int = 0


# ──────────────────────────────── Pagination ────────────────────────────────

class PaginatedRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    category: Optional[str] = None
    search: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: list = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
