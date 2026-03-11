"""
hadith_verifier.py
Multi-provider hadith verification pipeline.

Providers (in priority order):
1. dorar.net  — primary Arabic text search + grading (free, no key needed)
2. sunnah.com — enrichment via collection/number lookup (optional; needs SUNNAH_API_KEY)

Workflow:
  extract hadith text → dorar text search → get grade + source + sequence
                      → sunnah.com lookup by (source, sequence) → English text + cross-grade
                      → build HadithCitation with data from all providers

Reference links always provided (no API needed):
  dorar_url    → https://dorar.net/hadith?q={text}
  sunnah_url   → https://sunnah.com/{slug}:{seq}  (if source known)
  islamweb_url → https://www.islamweb.net/hadith/result.php?keywords={text}
"""
import os
import re
import html as _html_mod
import asyncio
import urllib.parse
from typing import Optional

import httpx

from api.models import HadithCitation


# ── API endpoints ────────────────────────────────────────────────────────────
_DORAR_API    = "https://dorar.net/hadith/api"
_DORAR_SEARCH = "https://dorar.net/hadith/search?searchType=word&st=w&test=1&q="
_SUNNAH_API   = "https://api.sunnah.com/v1"
_ISLAMWEB_SEARCH = "https://www.islamweb.net/hadith/result.php?language=A&keywords="

# sunnah.com API key — set SUNNAH_API_KEY env var to enable enrichment
_SUNNAH_KEY = os.getenv("SUNNAH_API_KEY", "")

_HTML_TAG = re.compile(r"<[^>]+>")

_GRADE_LABEL: dict[int, str] = {
    1: "صحيح",
    2: "حسن",
    3: "ضعيف",
    4: "موضوع",
}

# Maps dorar.net Arabic source names → sunnah.com collection slugs
_SOURCE_TO_SUNNAH: dict[str, str] = {
    "صحيح البخاري":   "bukhari",
    "صحيح مسلم":      "muslim",
    "سنن الترمذي":    "tirmidhi",
    "جامع الترمذي":   "tirmidhi",
    "سنن أبي داود":   "abudawud",
    "سنن النسائي":    "nasai",
    "سنن ابن ماجه":   "ibnmajah",
    "سنن ابن ماجة":   "ibnmajah",
    "موطأ مالك":      "malik",
    "مسند أحمد":      "ahmad",
    "صحيح ابن حبان":  "ibnhibban",
    "سنن الدارمي":    "darimi",
}


# ── Utilities ────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    return _html_mod.unescape(_HTML_TAG.sub("", text)).strip()


_TASHKEEL   = re.compile(r'[\u064B-\u065F\u0670]')
_NON_ARABIC = re.compile(r'[^\u0621-\u064A\u0671-\u06B7 ]')


def _normalize(text: str) -> str:
    """
    Full Arabic text normalization for comparison:
    strip tashkeel, normalize hamza/ta-marbuta/alef-maqsura, remove non-Arabic.
    """
    text = _TASHKEEL.sub("", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ؤ", "و").replace("ئ", "ي").replace("ة", "ه").replace("ى", "ي")
    text = _NON_ARABIC.sub(" ", text)
    return re.sub(r'\s+', ' ', text).strip()


def _word_overlap(a: str, b: str, min_len: int = 3) -> bool:
    """True if a and b share at least one significant Arabic word (≥ min_len chars)."""
    a_words = {w for w in _normalize(a).split() if len(w) >= min_len}
    b_words = {w for w in _normalize(b).split() if len(w) >= min_len}
    return bool(a_words & b_words)


def _word_overlap_score(a: str, b: str, min_len: int = 3) -> int:
    """Return count of shared significant words between a and b."""
    a_words = {w for w in _normalize(a).split() if len(w) >= min_len}
    b_words = {w for w in _normalize(b).split() if len(w) >= min_len}
    return len(a_words & b_words)


# ── Provider 1: dorar.net ────────────────────────────────────────────────────

async def _search_one(snippet: str) -> Optional[dict]:
    """
    Search dorar.net for a hadith by text snippet.
    Returns the best word-overlap matching result or None.
    """
    query = snippet[:80].strip()
    if len(query) < 8:
        return None
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                _DORAR_API,
                params={"q": query, "skey": "1", "page": "1"},
                headers={"User-Agent": "Ibn-Baz-Library/1.0"},
            )
            if resp.status_code != 200:
                return None
            ahadith = resp.json().get("ahadith", [])
            if not ahadith:
                return None
            norm_query = _normalize(query)
            query_words = {w for w in norm_query.split() if len(w) >= 3}

            # Collect all results that share at least one significant word with query.
            # Tuple: (score, deg, hadith_dict)
            candidates: list[tuple[int, int, dict]] = []
            for h in ahadith:
                clean = _strip_html(h.get("hadith", ""))
                h_words = {w for w in _normalize(clean).split() if len(w) >= 3}
                score = len(query_words & h_words)
                if score > 0:
                    deg = int(h.get("degree_cat") or 99)
                    candidates.append((score, deg, h))

            if not candidates:
                return None

            # Sort key: (-score, deg)
            #   • -score ASC  → highest overlap first (most relevant topic wins)
            #   • deg   ASC  → lowest degree_cat (best grade) breaks ties
            # Scenario A — same hadith, multiple chains ("من كذب علي متعمدا"):
            #   all 15 results share the same overlap score → grade breaks tie
            #   → degree_cat=1 (صحيح) beats degree_cat=3 (موضوع) ✓
            # Scenario B — different-topic hadiths sharing some words:
            #   the hadith with more matching words wins on overlap
            #   → correct topic returned regardless of grade ✓
            candidates.sort(key=lambda x: (-x[0], x[1]))
            return candidates[0][2]
    except Exception:
        return None


# ── Provider 2: sunnah.com ───────────────────────────────────────────────────

async def _enrich_sunnah(source: str, sequence: str, api_key: str) -> Optional[dict]:
    """
    Look up a hadith on sunnah.com by collection slug + number.
    Returns dict with {grade_en, text_en} or None if unavailable.
    Only called when source + sequence are known from dorar AND api_key is set.
    """
    if not api_key or not source or not sequence:
        return None
    slug = _SOURCE_TO_SUNNAH.get(source)
    if not slug:
        return None
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                f"{_SUNNAH_API}/collections/{slug}/hadiths/{sequence}",
                headers={"X-API-Key": api_key, "User-Agent": "Ibn-Baz-Library/1.0"},
            )
            if resp.status_code != 200:
                return None
            hadiths = resp.json().get("hadith", [])
            en_hadith = next((h for h in hadiths if h.get("lang") == "en"), None)
            if not en_hadith:
                return None
            grades = en_hadith.get("grades", [])
            grade_en = grades[0].get("grade", "") if grades else ""
            text_en = _strip_html(en_hadith.get("body", ""))
            # Strip leading "Narrated X:" prefix for cleaner display
            text_en = re.sub(r'^Narrated [^:]+:\s*', '', text_en).strip()
            return {"grade_en": grade_en, "text_en": text_en}
    except Exception:
        return None


# ── Enrichment & aggregation ─────────────────────────────────────────────────

def _build_urls(text: str, source: str, sequence: str) -> tuple[str, str]:
    """Build dorar_url and sunnah_url for a citation."""
    enc = urllib.parse.quote(text[:120], safe="")
    dorar_url = (_DORAR_SEARCH + enc) if text else ""

    slug = _SOURCE_TO_SUNNAH.get(source, "")
    # sunnah.com sequence must be a plain number (not volume/page like "4/221")
    plain_seq = sequence.strip()
    if slug and plain_seq and plain_seq.isdigit():
        sunnah_url = f"https://sunnah.com/{slug}:{plain_seq}"
    else:
        sunnah_url = ""  # Don't link without a valid hadith number
    return dorar_url, sunnah_url


def _enrich(citation: HadithCitation, dorar_result: dict,
             sunnah_data: Optional[dict] = None) -> HadithCitation:
    """Merge dorar.net result (and optional sunnah.com data) into a citation."""
    deg_cat   = int(dorar_result.get("degree_cat") or 0)
    clean_txt = _strip_html(dorar_result.get("hadith", ""))
    narrator  = dorar_result.get("rawi", "")
    grade_str = dorar_result.get("degree", "") or _GRADE_LABEL.get(deg_cat, "")
    source    = dorar_result.get("source", "")
    sequence  = str(dorar_result.get("sequence", "") or "")

    # Similarity guard: discard if dorar result is unrelated to what we searched
    if clean_txt and citation.text and not _word_overlap(citation.text, clean_txt):
        clean_txt = narrator = grade_str = source = sequence = ""
        deg_cat = 0

    # Use the verified API text for the dorar search URL (much more precise than
    # the user's query fragment — narrows the search to 1-2 narrations instead of many)
    dorar_search_text = clean_txt if clean_txt else citation.text
    dorar_url, sunnah_url = _build_urls(dorar_search_text, source, sequence)

    return HadithCitation(
        text           = citation.text,
        collection     = citation.collection or source,
        collector      = citation.collector,
        sunnah_url     = sunnah_url,
        verified_text  = clean_txt,
        narrator       = narrator,
        grade          = grade_str,
        grade_level    = deg_cat if clean_txt else 0,
        source_book    = source if clean_txt else "",
        dorar_url      = dorar_url,
        islamweb_url   = "",
        # sunnah.com cross-reference (populated only when API key is configured)
        sunnah_grade   = (sunnah_data or {}).get("grade_en", ""),
        sunnah_text_en = (sunnah_data or {}).get("text_en", ""),
    )


async def enrich_citations(citations: list[HadithCitation]) -> list[HadithCitation]:
    """
    Verify all citations against dorar.net in parallel, then enrich verified
    citations with sunnah.com data (if SUNNAH_API_KEY is set).

    Post-enrichment: deduplicates by normalized hadith text to prevent the same
    hadith appearing twice when detected by multiple pattern strategies.
    """
    if not citations:
        return citations

    # ── Phase 1: dorar.net text search (parallel) ────────────────────────────
    dorar_results = await asyncio.gather(
        *[_search_one(c.text) for c in citations],
        return_exceptions=True,
    )

    # ── Phase 2: sunnah.com enrichment (parallel, only if key + dorar found src) ─
    sunnah_tasks = []
    for citation, dorar_res in zip(citations, dorar_results):
        if isinstance(dorar_res, dict) and dorar_res and _SUNNAH_KEY:
            source   = dorar_res.get("source", "")
            sequence = str(dorar_res.get("sequence", "") or "")
            sunnah_tasks.append(_enrich_sunnah(source, sequence, _SUNNAH_KEY))
        else:
            sunnah_tasks.append(asyncio.sleep(0, result=None))  # no-op

    sunnah_results = await asyncio.gather(*sunnah_tasks, return_exceptions=True)

    # ── Phase 3: merge results ────────────────────────────────────────────────
    enriched: list[HadithCitation] = []
    for citation, dorar_res, sunnah_res in zip(citations, dorar_results, sunnah_results):
        sunnah_data = sunnah_res if isinstance(sunnah_res, dict) else None
        if isinstance(dorar_res, dict) and dorar_res:
            enriched.append(_enrich(citation, dorar_res, sunnah_data))
        else:
            # dorar unavailable — still provide search link
            dorar_url, sunnah_url = _build_urls(citation.text, "", "")
            enriched.append(citation.model_copy(update={
                "dorar_url":    dorar_url,
                "sunnah_url":   sunnah_url or citation.sunnah_url,
                "islamweb_url": "",
            }))

    # ── Post-enrichment dedup by normalized text ─────────────────────────────
    seen_norm: set[str] = set()
    deduped: list[HadithCitation] = []
    for c in enriched:
        display_text = c.verified_text or c.text
        norm_key = _normalize(display_text)[:60]
        if norm_key and norm_key in seen_norm:
            continue
        seen_norm.add(norm_key)
        deduped.append(c)

    return deduped
