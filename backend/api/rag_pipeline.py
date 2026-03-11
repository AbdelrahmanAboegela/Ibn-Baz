"""
rag_pipeline.py
Orchestrates the full RAG flow: Query → Retrieve → Expand Graph → Assemble → Generate.
"""
import re
import time
import urllib.parse

from typing import AsyncGenerator
from api.retriever import search_fatwas, get_related_fatwas, get_fatwas_by_ids
from api.generator import generate, generate_stream, RetrievalContext
from api.hadith_resolver import extract_citations as extract_hadith_citations
from api.hadith_verifier import (
    enrich_citations, _search_one, _strip_html, _normalize,
    _SOURCE_TO_SUNNAH, _ISLAMWEB_SEARCH,
)
from api.models import (
    ChatResponse,
    CitedFatwa,
    HadithCitation,
    QuranCitation,
    RAGResponse,
    RelatedFatwa,
)

# ── Hadith authenticity query detector ────────────────────────────────────────
# Matches Arabic queries asking about a hadith's grade/authenticity.
# Detects any query asking about hadith authenticity/grading — broad intentional match
_HADITH_QUERY_RE = re.compile(
    r'(?:'
    # Direct: صحة/صحه/صح حديث X
    r'صح[هة]?\s+(?:حديث|الحديث)'
    # هل + verb + حديث: هل صح/يصح/ثبت/يثبت/ورد/يرد/يحتج حديث X
    r'|هل\s+(?:صح|يصح|ثبت|يثبت|ورد|يرد|يحتج\s+ب|صحيح)\s+(?:حديث|الحديث)'
    # هل حديث X (حديث immediately after هل)
    r'|هل\s+(?:حديث|الحديث)\s+\S'
    # ما/كيف/اريد + صحة/درجة/حكم/مرتبة/رتبة/تخريج + حديث
    r'|(?:ما|كيف|اريد|ابغى)?\s*(?:صحة|درجة|حكم|مرتبة|رتبة|تخريج)\s+(?:حديث|الحديث)'
    # حديث X صحيح/ضعيف/موضوع/حسن؟
    r'|(?:حديث|الحديث)\s+\S.{2,80}(?:صحيح|ضعيف|موضوع|حسن|ثابت)'
    r')',
    re.UNICODE | re.IGNORECASE,
)

# After confirming it's a hadith query, extract the hadith text.
# Strategy: grab everything after "حديث"/"الحديث", then strip trailing grade words.
_HADITH_TEXT_RE = re.compile(
    r'(?:حديث|الحديث)\s+(.{3,150})',
    re.UNICODE | re.IGNORECASE,
)
# Words to strip from the END of extracted hadith text (they're part of the question, not the text)
_HADITH_TEXT_STRIP_TAIL = re.compile(
    r'\s*(?:صحيح|ضعيف|موضوع|حسن|ثابت|صحيح\s+ام\s+ضعيف|صح\s+ام\s+لا)[؟?]*\s*$',
    re.UNICODE | re.IGNORECASE,
)


async def _direct_hadith_lookup(query: str) -> dict | None:
    """
    If the query is asking about hadith authenticity, extract the hadith text
    and query dorar.net directly. Returns a dict with verification info for
    injection into the LLM prompt, or None if not a hadith query.
    """
    if not _HADITH_QUERY_RE.search(query):
        return None
    m = _HADITH_TEXT_RE.search(query)
    if not m:
        return None
    hadith_text = m.group(1).strip()
    hadith_text = _HADITH_TEXT_STRIP_TAIL.sub("", hadith_text).strip().rstrip('؟?').strip()
    if len(hadith_text) < 4:
        return None

    result = await _search_one(hadith_text)
    if not result:
        return None

    clean_txt = _strip_html(result.get("hadith", ""))
    deg_cat   = int(result.get("degree_cat") or 0)
    grade_map = {1: "صحيح", 2: "حسن", 3: "ضعيف", 4: "موضوع / ضعيف جداً"}

    return {
        "query_text":  hadith_text,
        "text":        clean_txt,
        "grade":       result.get("degree", grade_map.get(deg_cat, "")),
        "grade_cat":   deg_cat,
        "narrator":    result.get("rawi", ""),
        "source":      result.get("source", ""),
        "scholar":     result.get("mohadith", ""),
        "sequence":    str(result.get("sequence", "") or ""),
        "source_book": result.get("source", ""),
    }


def _build_hadith_verdict_response(
    query: str,
    info: dict,
    start_time: float,
) -> ChatResponse:
    """
    Bypass the LLM entirely for hadith authenticity queries.
    Generates a structured Arabic answer directly from dorar.net data.
    The LLM cannot hallucinate because it is never called.
    """
    from api.hadith_verifier import _SOURCE_TO_SUNNAH
    query_text = info["query_text"]
    verified   = info["text"]
    grade      = info["grade"]
    deg_cat    = info["grade_cat"]
    narrator   = info["narrator"]
    source     = info["source"]
    scholar    = info["scholar"]
    seq        = info["sequence"]

    # Verdict phrase and explanation based on grade category
    if deg_cat == 1:
        verdict  = "صحيح"
        verdict_detail = "ثابت بسند صحيح عن النبي ﷺ."
        confidence = 0.95
    elif deg_cat == 2:
        verdict  = "حسن"
        verdict_detail = "حسن الإسناد، ويُحتج به في الأحكام الشرعية."
        confidence = 0.90
    elif deg_cat == 3:
        verdict  = "ضعيف"
        verdict_detail = "ضعيف الإسناد، ولا يصح الاحتجاج به في الأحكام، وإن جاز ذكره في فضائل الأعمال عند بعض العلماء."
        confidence = 0.92
    else:
        verdict  = "موضوع أو شديد الضعف"
        verdict_detail = "لا يثبت عن النبي ﷺ، ولا يجوز نسبته إليه."
        confidence = 0.95

    # Build answer
    lines = [
        f"**الحكم على الحديث:** حديث «{query_text}» **{verdict}**.",
        "",
        f"**التفصيل:** {verdict_detail}",
        "",
    ]

    if verified:
        lines += [
            "**نص الحديث كما ورد في المصادر:**",
            f"> {verified}",
            "",
        ]

    details = []
    if narrator:
        details.append(f"الراوي: {narrator}")
    if source:
        details.append(f"المصدر: {source}")
    if scholar:
        details.append(f"حكم المحدث: {scholar} — **{grade}**")
    elif grade:
        details.append(f"الدرجة: **{grade}**")

    if details:
        lines += details
        lines.append("")

    if deg_cat >= 3:
        lines += [
            "**تنبيه:** لا يجوز الجزم بصحة هذا الحديث، وينبغي التثبت عند نسبة الأقوال إلى النبي ﷺ.",
            "",
        ]

    lines.append("*(المصدر: قاعدة بيانات الدرر السنية — dorar.net)*")

    answer = "\n".join(lines)

    # Build the HadithCitation for the block
    slug = _SOURCE_TO_SUNNAH.get(source, "")
    sunnah_url = (f"https://sunnah.com/{slug}:{seq}" if slug and seq else "")
    dorar_url    = "https://dorar.net/hadith/search?searchType=word&st=w&test=1&q=" + urllib.parse.quote(query_text[:80], safe="")
    islamweb_url = _ISLAMWEB_SEARCH + urllib.parse.quote(query_text[:80], safe="")

    citation = HadithCitation(
        text          = query_text,
        collection    = source,
        collector     = narrator,
        sunnah_url    = sunnah_url,
        verified_text = verified,
        narrator      = narrator,
        grade         = grade,
        grade_level   = deg_cat,
        source_book   = source,
        islamweb_url  = islamweb_url,
        dorar_url     = dorar_url,
    )

    return ChatResponse(
        answer          = answer,
        confidence      = confidence,
        hadith_citations= [citation],
        query_time_ms   = (time.time() - start_time) * 1000,
    )


async def run_rag_pipeline(query: str, top_k: int = 5) -> ChatResponse:
    """
    Full RAG pipeline:
    1. Retrieve top-k fatwas from Qdrant (dense search)
    2. Expand graph: fetch related fatwa titles via related_ids
    3. Collect Quran citations from retrieved fatwas
    4. Assemble context and run PydanticAI generator
    5. Build structured ChatResponse

    Special case: if the query is about hadith authenticity (صحة حديث X),
    we query dorar.net directly and return the verified grade WITHOUT calling
    the LLM — preventing any hallucination about hadith authenticity.
    """
    start_time = time.time()

    # ── Fast path: hadith authenticity query → bypass LLM ────────────────────
    direct_hadith_info = await _direct_hadith_lookup(query)
    if direct_hadith_info and direct_hadith_info.get("text"):
        return _build_hadith_verdict_response(query, direct_hadith_info, start_time)

    # ── Step 1: Retrieve ──
    retrieved = await search_fatwas(query, top_k=top_k)

    if not retrieved:
        return ChatResponse(
            answer="لم أجد فتاوى مرتبطة بسؤالك. يرجى إعادة صياغة السؤال.",
            confidence=0.0,
            query_time_ms=(time.time() - start_time) * 1000,
        )

    # ── Step 2: Graph expansion ──
    related_titles = []
    all_related_ids = set()
    for fatwa in retrieved:
        for rid in fatwa.get("related_ids", []):
            all_related_ids.add(rid)

    # Exclude already-retrieved IDs
    retrieved_ids = {f["fatwa_id"] for f in retrieved}
    expand_ids = list(all_related_ids - retrieved_ids)[:10]

    if expand_ids:
        related_fatwas = await get_fatwas_by_ids(expand_ids)
        related_titles = [r.get("title", "") for r in related_fatwas if r.get("title")]

    # ── Step 3: Collect Quran citations ──
    quran_citations = []
    seen_refs = set()
    for fatwa in retrieved:
        for citation in fatwa.get("quran_citations", []):
            ref = citation.get("reference", "")
            if ref and ref not in seen_refs:
                seen_refs.add(ref)
                quran_citations.append(citation)

    # ── Step 3b: Direct hadith lookup for authenticity queries ────────────────
    direct_hadith_info = await _direct_hadith_lookup(query)

    # ── Step 4: Assemble context and generate ──
    ctx = RetrievalContext(
        user_query=query,
        primary_fatwas=retrieved,
        related_titles=related_titles,
        quran_citations=quran_citations,
        hadith_verification=direct_hadith_info,
    )

    try:
        rag_response: RAGResponse = await generate(ctx)
    except Exception as e:
        # Fallback: return best retrieved fatwa as-is
        best = retrieved[0]
        return ChatResponse(
            answer=f"خطأ في التوليد. إليك أقرب فتوى:\n\n{best.get('answer', '')[:2000]}",
            confidence=0.3,
            cited_fatwas=[
                CitedFatwa(
                    fatwa_id=best["fatwa_id"],
                    title=best.get("title", ""),
                    source_ref=best.get("source_ref", ""),
                    url=best.get("url", ""),
                    relevance_score=best.get("_score", 0.0),
                )
            ],
            query_time_ms=(time.time() - start_time) * 1000,
        )

    # ── Step 5: Build response ──
    cited_fatwas = []
    for fatwa in retrieved:
        fid = fatwa["fatwa_id"]
        cited_fatwas.append(
            CitedFatwa(
                fatwa_id=fid,
                title=fatwa.get("title", ""),
                source_ref=fatwa.get("source_ref", ""),
                url=fatwa.get("url", ""),
                relevance_score=fatwa.get("_score", 0.0),
            )
        )

    quran_models = [QuranCitation(**c) for c in quran_citations]

    hadith_raw    = extract_hadith_citations(rag_response.answer)
    hadith_models = await enrich_citations(hadith_raw)

    # Prepend direct-lookup hadith (from صحة حديث query) if present
    if direct_hadith_info and direct_hadith_info.get("text"):
        from api.hadith_verifier import _SOURCE_TO_SUNNAH
        src = direct_hadith_info.get("source_book", "")
        seq = direct_hadith_info.get("sequence", "")
        slug = _SOURCE_TO_SUNNAH.get(src, "")
        sunnah_url = (f"https://sunnah.com/{slug}:{seq}" if slug and seq else "")
        dorar_url = "https://dorar.net/hadith/search?searchType=word&st=w&test=1&q=" + urllib.parse.quote(
            direct_hadith_info.get("query_text", "")[:80], safe=""
        )
        deg_cat = direct_hadith_info.get("grade_cat", 0)
        grade_map = {1: "صحيح", 2: "حسن", 3: "ضعيف", 4: "موضوع"}
        direct_citation = HadithCitation(
            text          = direct_hadith_info.get("query_text", ""),
            collection    = src,
            collector     = direct_hadith_info.get("narrator", ""),
            sunnah_url    = sunnah_url,
            verified_text = direct_hadith_info.get("text", ""),
            narrator      = direct_hadith_info.get("narrator", ""),
            grade         = direct_hadith_info.get("grade", grade_map.get(deg_cat, "")),
            grade_level   = deg_cat,
            source_book   = src,
            dorar_url     = dorar_url,
        )
        # Only prepend if not already in the list
        from api.hadith_verifier import _normalize
        direct_norm = _normalize(direct_citation.verified_text or direct_citation.text)[:50]
        already_present = any(
            _normalize(c.verified_text or c.text)[:50] == direct_norm for c in hadith_models
        )
        if not already_present:
            hadith_models = [direct_citation] + hadith_models

    related_models = [
        RelatedFatwa(fatwa_id=rid, title=title)
        for rid, title in zip(expand_ids, related_titles)
        if title
    ]

    return ChatResponse(
        answer=rag_response.answer,
        confidence=rag_response.confidence,
        cited_fatwas=cited_fatwas,
        quran_citations=quran_models,
        hadith_citations=hadith_models,
        related_fatwas=related_models,
        query_time_ms=(time.time() - start_time) * 1000,
    )


async def run_rag_pipeline_stream(query: str, top_k: int = 5) -> AsyncGenerator[dict, None]:
    """
    Streaming RAG pipeline:
    Yields chunks of text in real-time, then yields metadata at the end.

    Special case: if the query is about hadith authenticity (صحة حديث X),
    we return the verified answer from dorar.net without streaming the LLM.
    """
    start_time = time.time()

    # ── Fast path: hadith authenticity query → bypass LLM ────────────────────
    direct_hadith_info = await _direct_hadith_lookup(query)
    if direct_hadith_info and direct_hadith_info.get("text"):
        response = _build_hadith_verdict_response(query, direct_hadith_info, start_time)
        # Emit the full answer as a single chunk so the frontend renders it
        yield {"type": "chunk", "content": response.answer}
        yield {"type": "metadata", "content": response.model_dump()}
        return

    # Step 1: Retrieve
    retrieved = await search_fatwas(query, top_k=top_k)

    if not retrieved:
        yield {
            "type": "metadata",
            "content": ChatResponse(
                answer="لم أجد فتاوى مرتبطة بسؤالك. يرجى إعادة صياغة السؤال.",
                confidence=0.0,
                query_time_ms=(time.time() - start_time) * 1000,
            ).model_dump()
        }
        return

    # Step 2: Graph expansion
    related_titles = []
    all_related_ids = set()
    for fatwa in retrieved:
        for rid in fatwa.get("related_ids", []):
            all_related_ids.add(rid)

    retrieved_ids = {f["fatwa_id"] for f in retrieved}
    expand_ids = list(all_related_ids - retrieved_ids)[:10]

    if expand_ids:
        related_fatwas = await get_fatwas_by_ids(expand_ids)
        related_titles = [r.get("title", "") for r in related_fatwas if r.get("title")]

    # Step 3: Collect Quran citations
    quran_citations = []
    seen_refs = set()
    for fatwa in retrieved:
        for citation in fatwa.get("quran_citations", []):
            ref = citation.get("reference", "")
            if ref and ref not in seen_refs:
                seen_refs.add(ref)
                quran_citations.append(citation)

    # Step 3b: No longer needed here — hadith queries handled at top of function.
    # Step 4: Assemble context
    ctx = RetrievalContext(
        user_query=query,
        primary_fatwas=retrieved,
        related_titles=related_titles,
        quran_citations=quran_citations,
        hadith_verification=None,
    )

    full_answer = ""
    try:
        async for chunk in generate_stream(ctx):
            if chunk:
                full_answer += chunk
                yield {"type": "chunk", "content": chunk}
    except Exception as e:
        yield {"type": "error", "content": str(e)}
        return

    # Optional: sanitize full answer 
    from api.generator import _sanitize
    full_answer = _sanitize(full_answer)

    # Step 5: Build metadata response
    cited_fatwas = []
    for fatwa in retrieved:
        fid = fatwa["fatwa_id"]
        cited_fatwas.append(
            CitedFatwa(
                fatwa_id=fid,
                title=fatwa.get("title", ""),
                source_ref=fatwa.get("source_ref", ""),
                url=fatwa.get("url", ""),
                relevance_score=fatwa.get("_score", 0.0),
            )
        )

    quran_models = [QuranCitation(**c) for c in quran_citations]

    hadith_raw    = extract_hadith_citations(full_answer)
    hadith_models = await enrich_citations(hadith_raw)

    related_models = [
        RelatedFatwa(fatwa_id=rid, title=title)
        for rid, title in zip(expand_ids, related_titles)
        if title
    ]

    top_score = ctx.primary_fatwas[0].get("_score", 0.7) if ctx.primary_fatwas else 0.5
    confidence = min(round(float(top_score), 2), 1.0)

    response = ChatResponse(
        answer=full_answer,
        confidence=confidence,
        cited_fatwas=cited_fatwas,
        quran_citations=quran_models,
        hadith_citations=hadith_models,
        related_fatwas=related_models,
        query_time_ms=(time.time() - start_time) * 1000,
    )

    yield {"type": "metadata", "content": response.model_dump()}
