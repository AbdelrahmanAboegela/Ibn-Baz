"""
generator.py
Handles LLM generation for the RAG pipeline.
"""
import re
import os
import sys
from typing import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
from api.models import RAGResponse


# ─── Dependency type ─────────────────────────────────────────────────────────

@dataclass
class RetrievalContext:
    """Typed dependency: injected into the generator at run-time."""
    user_query: str
    primary_fatwas: list[dict]              # top-k retrieved fatwas
    related_titles: list[str]               # from graph expansion
    quran_citations: list[dict]             # verified Quran verses
    hadith_verification: dict | None = None # direct dorar.net lookup result (for صحة حديث queries)


# ─── Client ──────────────────────────────────────────────────────────────────

_client = AsyncOpenAI(
    api_key=settings.fanar_api_key,
    base_url="https://api.fanar.qa/v1"
)


# ─── Output sanitiser ────────────────────────────────────────────────────────
# Strip stray CJK, Cyrillic, or other non-relevant scripts that sometimes
# appear as LLM artefacts/hallucinations in the raw completion.
_GARBAGE = re.compile(
    r"[\u4e00-\u9fff"      # CJK unified ideographs (Chinese/Japanese/Korean)
    r"\u3040-\u30ff"       # Hiragana + Katakana
    r"\uac00-\ud7af"       # Korean Hangul syllables
    r"\u0400-\u04ff"       # Cyrillic
    r"\u0900-\u097f"       # Devanagari
    r"\u0e00-\u0e7f]+"     # Thai
)

# Strip XML-style wrapper tags the LLM may emit despite prompt instructions
# e.g. <quran_start>, </quran_end>, <hadith_start>, <hadith_end>
_XML_TAGS = re.compile(r"</?(?:quran|hadith|ayah|verse|citation)(?:_\w+)?(?:\s[^>]*)?>", re.IGNORECASE)

def _sanitize(text: str) -> str:
    text = _XML_TAGS.sub("", text)
    return _GARBAGE.sub("", text).strip()


# ─── Prompt builder ──────────────────────────────────────────────────────────

_SYSTEM = """\
أنت الشيخ ابن باز (رحمه الله) — المفتي العام السابق للمملكة العربية السعودية وأحد كبار علماء الإسلام في القرن العشرين.

# قواعد الإجابة (يجب الالتزام بها)

1. **اللغة**: أجب بالعربية الفصيحة دائماً، مهما كانت لغة السؤال.
2. **المصادر الشرعية**: استند حصراً إلى الفتاوى المقدمة في السياق. لا تخترع فتاوى أو أحاديث.
3. **درجة الحديث**: لا تحكم على صحة أي حديث أو ضعفه من نفسك. إن سُئلت عن صحة حديث فقل ما ورد في الفتاوى المقدمة فقط، ولا تجزم بصحته أو ضعفه من غير دليل من السياق.
4. **الاستشهاد بالقرآن الكريم**: عند ذكر آية قرآنية، اكتب نصها كاملاً وأتبعها بقوسين معقوفين واسم السورة ورقم الآية: {الآية} [سورة: رقمها].
5. **الاستشهاد بالحديث النبوي**: عند ذكر حديث، اذكر نصه أو معناه وأتبعه بـ: (رواه البخاري) أو (رواه مسلم) أو الراوي المذكور في المصدر — فقط إذا ورد في السياق.
6. **الاستشهاد بالفتاوى**: أشر إلى رقم الفتوى بين قوسين [فتوى: رقم] عند الاستناد إليها.
7. **الهيكل**: نظّم إجابتك بوضوح:
   - ابدأ بالحكم الشرعي مباشرة
   - ثم الأدلة من القرآن والسنة (من السياق فقط)
   - ثم الفتاوى التفصيلية ذات الصلة
   - واختم بالتوصية الشرعية العملية
8. **الموضوعية**: إن كان الموضوع خارج نطاق السياق، صرّح بذلك باختصار ولا تتكهن.
9. **الشمولية**: كن وافياً ودقيقاً. اذكر الخلاف الفقهي إن وُجد في المصادر.
10. **التحريم**: لا تُفتِ في أمر لم يرد في السياق المُقدَّم — قل «لم أجد هذه المسألة في الفتاوى المتاحة» إذا لزم.
11. **تنسيق الآيات**: يُمنع منعاً باتاً استخدام وسوم مثل <quran_start> أو <quran_end> أو وضع روابط خارجية (مثل quran.com). اكتب الآية كنص عادي مجرد.
"""

def _build_prompt(ctx: RetrievalContext) -> tuple[str, str]:
    """Return (system_prompt, user_message)."""

    # Format retrieved fatwas
    fatwas_lines = []
    for f in ctx.primary_fatwas:
        answer_text = (f.get("answer") or f.get("answer_direct") or "")[:2000]
        lines = [
            f"┌── [فتوى {f['fatwa_id']}] {f.get('title', '')}",
            f"│ السؤال: {f.get('question', '')[:400]}",
            f"│ الجواب: {answer_text}",
            f"│ المصدر: {f.get('source_ref', '')}",
            "└──",
        ]
        fatwas_lines.append("\n".join(lines))
    fatwas_block = "\n\n".join(fatwas_lines) if fatwas_lines else "لا توجد فتاوى متعلقة بهذا السؤال في قاعدة البيانات."

    # Format Quran citations
    if ctx.quran_citations:
        quran_lines = []
        for q in ctx.quran_citations:
            ref  = q.get("reference", "")
            text = q.get("verified_text", "")
            url  = q.get("quran_url", "")
            if text and ref:
                quran_lines.append(f"• {{{text}}} [{ref}]")
            elif ref:
                quran_lines.append(f"• [{ref}]")
        quran_block = "\n".join(quran_lines)
    else:
        quran_block = "لم يتم استخراج آيات قرآنية مرتبطة بهذا السؤال."

    user_msg = (
        f"السؤال: {ctx.user_query}\n\n"
        "═══════════════════════════════════════════\n"
        "السياق الشرعي من فتاوى الشيخ ابن باز:\n"
        "═══════════════════════════════════════════\n"
        f"{fatwas_block}\n\n"
        "═══════════════════════════════════════════\n"
        "الآيات القرآنية المرتبطة من الفتاوى:\n"
        "═══════════════════════════════════════════\n"
        f"{quran_block}\n\n"
    )

    # ── Inject dorar hadith verification (for صحة حديث queries) ──────────────
    if ctx.hadith_verification:
        v = ctx.hadith_verification
        hadith_text = v.get("text", "")
        grade       = v.get("grade", "")
        grade_label = {"1": "صحيح", "2": "حسن", "3": "ضعيف", "4": "موضوع / ضعيف جداً"}.get(
            str(v.get("grade_cat", "")), grade
        )
        narrator    = v.get("narrator", "")
        source      = v.get("source", "")
        scholar     = v.get("scholar", "")
        user_msg += (
            "═══════════════════════════════════════════\n"
            "نتيجة التحقق من الحديث عبر قاعدة بيانات الدرر السنية:\n"
            "═══════════════════════════════════════════\n"
            f"نص الحديث: {hadith_text}\n"
            f"درجة الحديث: {grade_label}\n"
        )
        if narrator:
            user_msg += f"الراوي: {narrator}\n"
        if source:
            user_msg += f"المصدر: {source}\n"
        if scholar:
            user_msg += f"الحكم من: {scholar}\n"
        user_msg += (
            "\n⚠️ تعليمات مهمة: يجب أن تستند إجابتك عن صحة هذا الحديث إلى نتيجة التحقق أعلاه فقط. "
            f"لا تجزم بصحة الحديث إن لم تكن درجته صحيحاً أو حسناً. "
            f"الدرجة الموثقة هي: {grade_label}.\n\n"
        )

    user_msg += (
        "التعليمات:\n"
        "- أجب بشكل مفصّل ومنظّم مستنداً إلى الفتاوى والآيات أعلاه فقط.\n"
        "- استشهد بكل آية مذكورة مع اسم سورتها ورقمها بين قوسين.\n"
        "- أشر إلى أرقام الفتاوى عند الاستناد إليها [فتوى: رقم].\n"
        "- إن ورد حديث نبوي في الفتاوى، اذكره مع مصدره.\n"
    )

    return _SYSTEM, user_msg


# ─── Generate ─────────────────────────────────────────────────────────────────

async def generate_stream(ctx: RetrievalContext) -> AsyncGenerator[str, None]:
    """
    Call Fanar API and stream the response back in real-time.
    """
    system_prompt, user_message = _build_prompt(ctx)

    stream = await _client.chat.completions.create(
        model=settings.fanar_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.15,
        max_tokens=3000,
        stream=True,
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content


async def generate(ctx: RetrievalContext) -> RAGResponse:
    """
    Call Groq API with a strict scholarly prompt.
    Sanitises output to remove any LLM garbage characters.
    """
    system_prompt, user_message = _build_prompt(ctx)

    completion = await _client.chat.completions.create(
        model=settings.fanar_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.15,         # very low for factual, reproducible Islamic opinions
        max_tokens=3000,          # enough for a thorough, multi-source answer
    )

    raw_answer = completion.choices[0].message.content or ""
    answer = _sanitize(raw_answer)  # strip CJK/Cyrillic artefacts

    # Confidence from retrieval score
    top_score = ctx.primary_fatwas[0].get("_score", 0.7) if ctx.primary_fatwas else 0.5
    confidence = min(round(float(top_score), 2), 1.0)

    return RAGResponse(
        answer=answer,
        confidence=confidence,
        cited_fatwa_ids=[f["fatwa_id"] for f in ctx.primary_fatwas if f.get("fatwa_id")],
        cited_quran_refs=[q.get("reference", "") for q in ctx.quran_citations if q.get("reference")],
    )
