"""
generator.py
Direct Groq API generation — no structured JSON output so the model can write
a full, untruncated Arabic answer. PydanticAI was causing truncation because
the small model had to simultaneously generate a long answer AND close the JSON.
"""
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from groq import AsyncGroq

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
from api.models import RAGResponse


# ──────────────────────────────── Dependency type ────────────────────────────────

@dataclass
class RetrievalContext:
    """Typed dependency: injected into the generator at run-time."""
    user_query: str
    primary_fatwas: list[dict]       # top-k retrieved fatwas
    related_titles: list[str]        # from graph expansion
    quran_citations: list[dict]      # verified Quran verses


# ──────────────────────────────── Client ────────────────────────────────

_client = AsyncGroq(api_key=settings.groq_api_key)


# ──────────────────────────────── Prompt builder ────────────────────────────────

def _build_prompt(ctx: RetrievalContext) -> tuple[str, str]:
    """Return (system_prompt, user_message)."""

    system = (
        "أنت مساعد متخصص في فتاوى الشيخ عبد العزيز بن عبد الله بن باز رحمه الله، "
        "المفتي العام للمملكة العربية السعودية سابقاً. "
        "أجب باللغة العربية الفصيحة استناداً إلى السياق المقدم من فتاوى الشيخ فقط. "
        "لا تخترع معلومات خارج السياق المقدم. "
        "اذكر رقم الفتوى ومصدرها عند الاستشهاد عند الإمكان. "
        "كن شاملاً ودقيقاً، واذكر الحكم الشرعي وأدلته من الفتاوى المقدمة."
    )

    # Format retrieved fatwas (limit each to 1500 chars to save tokens)
    fatwas_block = "\n\n".join(
        f"[فتوى {f['fatwa_id']}] {f.get('title', '')}\n"
        f"السؤال: {f.get('question', '')}\n"
        f"الجواب: {(f.get('answer', '') or f.get('answer_direct', ''))[:1500]}\n"
        f"المصدر: {f.get('source_ref', '')}"
        for f in ctx.primary_fatwas
    )

    # Quran citations
    quran_block = "\n".join(
        f"[{q.get('reference', '')}] {q.get('verified_text', '')}"
        for q in ctx.quran_citations
    ) or "لا توجد آيات محددة"

    user_msg = (
        f"السؤال: {ctx.user_query}\n\n"
        f"السياق من فتاوى الشيخ ابن باز:\n"
        f"{'='*60}\n"
        f"{fatwas_block}\n\n"
        f"{'='*60}\n"
        f"آيات قرآنية ذات صلة:\n{quran_block}\n\n"
        f"الرجاء الإجابة على السؤال بشكل مفصل ومنظم بناءً على الفتاوى أعلاه."
    )

    return system, user_msg


# ──────────────────────────────── Generate ────────────────────────────────

async def generate(ctx: RetrievalContext) -> RAGResponse:
    """
    Call Groq API directly for plain-text generation.
    No structured JSON output → model can write a complete, untruncated answer.
    """
    system_prompt, user_message = _build_prompt(ctx)

    completion = await _client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.2,          # low temp for factual Islamic content
        max_tokens=2048,          # enough for a thorough answer
    )

    answer = completion.choices[0].message.content or ""

    # Derive confidence from top retrieval score
    top_score = ctx.primary_fatwas[0].get("_score", 0.7) if ctx.primary_fatwas else 0.5
    confidence = min(round(float(top_score), 2), 1.0)

    return RAGResponse(
        answer=answer,
        confidence=confidence,
        cited_fatwa_ids=[f["fatwa_id"] for f in ctx.primary_fatwas if f.get("fatwa_id")],
        cited_quran_refs=[q.get("reference", "") for q in ctx.quran_citations if q.get("reference")],
    )
