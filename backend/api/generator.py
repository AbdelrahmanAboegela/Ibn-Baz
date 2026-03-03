"""
generator.py
PydanticAI Agent with Groq (llama-3.3-70b-versatile).
Produces structured RAGResponse with citations, validated at runtime.
"""
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
from api.models import RAGResponse

# Ensure Groq key is set
os.environ.setdefault("GROQ_API_KEY", settings.groq_api_key)


# ──────────────────────────────── Dependency type ────────────────────────────────

@dataclass
class RetrievalContext:
    """Typed dependency: injected into the agent at run-time."""
    user_query: str
    primary_fatwas: list[dict]       # top-k retrieved fatwas
    related_titles: list[str]        # from graph expansion
    quran_citations: list[dict]      # verified Quran verses


# ──────────────────────────────── Agent Setup ────────────────────────────────

# Create the Groq model
_groq_model = GroqModel(
    settings.groq_model,
    provider=GroqProvider(api_key=settings.groq_api_key),
)

# The PydanticAI Agent — typed over (RetrievalContext, RAGResponse)
agent = Agent(
    model=_groq_model,
    output_type=RAGResponse,
    deps_type=RetrievalContext,
)


# ──────────────────────────────── System Prompts ────────────────────────────────

@agent.system_prompt
def arabic_system_prompt() -> str:
    """Static system prompt defining the assistant's role."""
    return (
        "أنت مساعد متخصص في فتاوى الشيخ عبد العزيز بن عبد الله بن باز رحمه الله، "
        "المفتي العام للمملكة العربية السعودية سابقاً وأحد أبرز علماء الأمة الإسلامية. "
        "أجب باللغة العربية فقط استناداً إلى السياق المقدم من فتاوى الشيخ. "
        "لا تخترع معلومات خارج السياق المقدم. "
        "اذكر رقم الفتوى ومصدرها عند الاستشهاد. "
        "اذكر الآيات القرآنية بنصها الكامل إذا وردت في السياق. "
        "كن دقيقاً وأميناً في النقل عن الشيخ ابن باز."
    )


@agent.system_prompt
def inject_context(ctx: RunContext[RetrievalContext]) -> str:
    """Dynamic system prompt: formats retrieved fatwas + Quran into context block."""
    c = ctx.deps

    # Format retrieved fatwas
    fatwas_block = "\n\n".join(
        f"[فتوى {f['fatwa_id']}] {f.get('title', '')}\n"
        f"السؤال: {f.get('question', '')}\n"
        f"الجواب: {f.get('answer', '')[:2000]}\n"
        f"المصدر: {f.get('source_ref', '')}"
        for f in c.primary_fatwas
    )

    # Format Quran citations
    quran_block = "\n".join(
        f"[{q.get('reference', '')}] {q.get('verified_text', '')}"
        for q in c.quran_citations
    ) if c.quran_citations else "لا توجد آيات قرآنية محددة في السياق"

    # Format related fatwas
    related_block = "، ".join(c.related_titles[:10]) if c.related_titles else "لا توجد"

    return (
        f"السياق المسترجع من فتاوى الشيخ ابن باز:\n"
        f"{'='*50}\n"
        f"{fatwas_block}\n\n"
        f"{'='*50}\n"
        f"الآيات القرآنية الموثقة:\n{quran_block}\n\n"
        f"فتاوى ذات صلة: {related_block}"
    )


# ──────────────────────────────── Generate ────────────────────────────────

async def generate(ctx: RetrievalContext) -> RAGResponse:
    """
    Run the PydanticAI agent with the retrieval context.
    Returns a Pydantic-validated RAGResponse.
    """
    result = await agent.run(ctx.user_query, deps=ctx)
    return result.output
