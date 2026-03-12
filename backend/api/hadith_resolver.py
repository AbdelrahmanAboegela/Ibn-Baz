"""
hadith_resolver.py
Detects hadith attributions in Arabic text (fatwa answers, LLM output)
and produces structured HadithCitation objects.

Detection strategies (all combined, ordered by specificity):
  1. Prophetic-speech: قال ﷺ / قال رسول الله: TEXT (extracts the actual hadith body)
  2. Trigger-verb: رواه X / أخرجه X — snippet BEFORE trigger is the hadith text
  3. Direct "في صحيح X" / "وفي صحيح X" — snippet AFTER reference, refined past any قال:
  4. Parenthetical attribution: (رواه البخاري) / (متفق عليه)
  5. Standalone "متفق عليه"

All results are deduplicated by collection slug and sorted by first appearance.
"""
import re
from api.models import HadithCitation

_SUNNAH_BASE = "https://sunnah.com/"
_DORAR_SEARCH = "https://dorar.net/hadith/search?searchType=word&st=w&test=1&q="

_BOUNDARY     = re.compile(r"[.،؛\n]")
_LEADING_JUNK = re.compile(r'^[\s"\'«»\u201c\u201d\u201e\[\]،؛.(،\u200f\u200e\ufeff]+')
_TRAILING_JUNK= re.compile(r'[\s"\'«»\u201c\u201d\u201e\[\]،؛.،\u200f\u200e\ufeff]+$')
_QURAN_REF    = re.compile(r'\[[\u0600-\u06FF]{2,20}\s*:\s*\d{1,3}\]')
_FATWA_REF    = re.compile(r'\[فتوى[:\s]*[\d,،\s]+\]', re.UNICODE)
_OUTER_QUOTES = re.compile(r'^[«""„\u201c](.*)[»""\u201d]$', re.UNICODE | re.DOTALL)
# Attribution tail patterns to strip from the end of a detected snippet
_ATTR_TAIL    = re.compile(
    r'\s*(?:متفق\s+عليه|رواه\s+\S+|أخرجه\s+\S+|من\s+حديث\s+\S+)'
    r'[\s\S]{0,60}$',
    re.UNICODE,
)


def _clean(text: str) -> str:
    text = _QURAN_REF.sub("", text)
    text = _FATWA_REF.sub("", text)          # strip [فتوى: 18003, 7987]
    text = _LEADING_JUNK.sub("", text)
    text = _TRAILING_JUNK.sub("", text)
    text = _ATTR_TAIL.sub("", text)
    text = text.strip()
    # Strip surrounding quotation marks (hadiths are often quoted verbatim)
    m = _OUTER_QUOTES.match(text)
    if m:
        text = m.group(1).strip()
    return text


def _refine_after_qala(text: str) -> str:
    """If snippet includes narrator prefix 'قال:', extract only text after last colon."""
    for marker in ("قالَ ﷺ:", "قالَ عليه الصلاة والسلام:", "قال ﷺ:",
                   "قال عليه الصلاة والسلام:", "قال عليه السلام:", "قال:"):
        idx = text.rfind(marker)
        if idx >= 0:
            return text[idx + len(marker):].strip()
    return text.strip()


def _snippet_before(text: str, pos: int, max_chars: int = 250) -> str:
    raw = text[max(0, pos - max_chars): pos]
    parts = list(_BOUNDARY.finditer(raw))
    if parts:
        candidate = _clean(raw[parts[-1].end():])
        if len(candidate) >= 12:
            return candidate
        # Attribution trigger immediately follows a sentence boundary (e.g. a period).
        # Fall back to the previous sentence segment.
        if len(parts) >= 2:
            return _clean(raw[parts[-2].end(): parts[-1].start()])
        else:
            return _clean(raw[: parts[-1].start()])
    return _clean(raw)


def _snippet_after(text: str, pos: int, max_chars: int = 320) -> str:
    raw = text[pos: pos + max_chars]
    parts = list(_BOUNDARY.finditer(raw))
    if parts:
        raw = raw[: parts[0].start()]
    raw = _refine_after_qala(raw)
    return _clean(raw)


# Ordered longest-match-first so "صحيح البخاري" beats "البخاري"
_COLLECTIONS: list[tuple[str, str, str]] = [
    ("صحيح البخاري",  "الإمام البخاري",      "bukhari"),
    ("صحيح مسلم",     "الإمام مسلم",          "muslim"),
    ("الصحيحين",      "البخاري ومسلم",        "bukhari"),
    ("متفق عليه",     "البخاري ومسلم",        "bukhari"),
    ("موطأ مالك",     "الإمام مالك",          "malik"),
    ("مسند أحمد",     "الإمام أحمد",          "ahmad"),
    ("ابن أبي شيبة",  "الإمام ابن أبي شيبة", "ibnabishaybah"),
    ("ابن خزيمة",     "الإمام ابن خزيمة",    "ibnkhuzaymah"),
    ("ابن حبان",      "الإمام ابن حبان",      "ibnhibban"),
    ("ابن ماجه",      "الإمام ابن ماجه",      "ibnmajah"),
    ("ابن ماجة",      "الإمام ابن ماجه",      "ibnmajah"),
    ("الدارقطني",     "الإمام الدارقطني",     "daraqutni"),
    ("الطبراني",      "الإمام الطبراني",      "tabarani"),
    ("الدارمي",       "الإمام الدارمي",       "darimi"),
    ("البيهقي",       "الإمام البيهقي",       "bayhaqi"),
    ("الحاكم",        "الإمام الحاكم",        "hakim"),
    ("الترمذي",       "الإمام الترمذي",       "tirmidhi"),
    ("ترمذي",         "الإمام الترمذي",       "tirmidhi"),
    ("النسائي",       "الإمام النسائي",       "nasai"),
    ("نسائي",         "الإمام النسائي",       "nasai"),
    ("أبو داود",      "الإمام أبو داود",      "abudawud"),
    ("أبي داود",      "الإمام أبو داود",      "abudawud"),
    ("البخاري",       "الإمام البخاري",       "bukhari"),
    ("مسلم",          "الإمام مسلم",          "muslim"),
    ("أحمد",          "الإمام أحمد",          "ahmad"),
    ("مالك",          "الإمام مالك",          "malik"),
]


def _collection_for(text: str) -> tuple | None:
    for kw, collector, slug in _COLLECTIONS:
        if kw in text:
            return kw, collector, slug
    return None


# ── Pattern 1: Prophetic-speech ───────────────────────────────────────────────
# No tashkeel — LLM outputs plain Arabic without diacritics.
# Allows optional context between prophet's title and colon:
#   قال النبي ﷺ: TEXT
#   قال النبي ﷺ في التمر لما قال له بلال: TEXT
#   فقال النبي لبعض الحاضرين: TEXT
_PROPHETIC = re.compile(
    "(?:ثم قال|وقال|فقال|قال|يقول|ويقول|فيقول)\\s+(?:"
    "(?:عليه\\s+(?:الصلاة\\s+و)?(?:التسليم|السلام))"   # عليه الصلاة والسلام
    "|(?:النبي\\s*\ufdfa?)"                              # النبي / النبي ﷺ
    "|(?:رسول\\s+الله\\s*\ufdfa?)"                      # رسول الله / رسول الله ﷺ
    "|\ufdfa"                                            # bare ﷺ symbol
    ")[^:،؛\n]{0,60}[:\\u2013\\-]\\s*(.{10,300})",
    re.UNICODE | re.DOTALL,
)

# ── Pattern 2: Trigger verbs ──────────────────────────────────────────────────
# "رواه البخاري", "رواه الإمام مسلم", "روى مسلم في صحيحه", "أخرجه مسلم", "علقه البخاري" etc.
# Also: "يروى عن النبي ﷺ", "ذكر ذلك البخاري", "متفق على صحته"
_TRIGGER = re.compile(
    r'(?:رواه|روى|يروى|أخرجه|خرّجه|خرجه|أخرج|صحّحه|صححه|ذكره|ذكر\s+ذلك|نقله|حسّنه|حسنه|علّقه|علقه|متفق\s+على|متفق\s+عليه)\s+',
    re.UNICODE,
)
# Honorary prefix "الإمام" sometimes separates trigger from collection name
_IMAM_PREFIX = re.compile(r'^(?:الإمام\s+|إمام\s+|الحافظ\s+|الشيخ\s+)?', re.UNICODE)

# ── Pattern 3: Direct collection references ───────────────────────────────────
_DIRECT: list[tuple] = [
    (re.compile(r'(?:وفي|في|ففي)\s+صحيح\s+البخاري',           re.UNICODE), "صحيح البخاري", "الإمام البخاري",   "bukhari"),
    (re.compile(r'(?:وفي|في|ففي)\s+صحيح\s+مسلم',              re.UNICODE), "صحيح مسلم",    "الإمام مسلم",      "muslim"),
    (re.compile(r'(?:وفي|في|ففي)\s+الصحيحين',                 re.UNICODE), "الصحيحين",     "البخاري ومسلم",    "bukhari"),
    (re.compile(r'(?:وفي|في|ففي)\s+(?:سنن\s+)?أبي?\s+داود',   re.UNICODE), "أبو داود",     "الإمام أبو داود",  "abudawud"),
    (re.compile(r'(?:وفي|في|ففي)\s+(?:سنن\s+)?الترمذي',       re.UNICODE), "الترمذي",      "الإمام الترمذي",   "tirmidhi"),
    (re.compile(r'(?:وفي|في|ففي)\s+(?:سنن\s+)?النسائي',       re.UNICODE), "النسائي",      "الإمام النسائي",   "nasai"),
    (re.compile(r'(?:وفي|في|ففي)\s+(?:سنن\s+)?ابن\s+ماج[هة]', re.UNICODE), "ابن ماجه",    "الإمام ابن ماجه",  "ibnmajah"),
    (re.compile(r'(?:وفي|في|ففي)\s+(?:مسند\s+)?أحمد',         re.UNICODE), "مسند أحمد",   "الإمام أحمد",      "ahmad"),
    (re.compile(r'(?:وفي|في|ففي)\s+(?:موطأ?\s+)?مالك',        re.UNICODE), "موطأ مالك",   "الإمام مالك",      "malik"),
    (re.compile(r'(?:وفي|في|ففي)\s+البيهقي',                  re.UNICODE), "البيهقي",      "الإمام البيهقي",   "bayhaqi"),
    (re.compile(r'(?:وفي|في|ففي)\s+الطبراني',                 re.UNICODE), "الطبراني",     "الإمام الطبراني",  "tabarani"),
    (re.compile(r'(?:وفي|في|ففي)\s+الحاكم',                   re.UNICODE), "الحاكم",       "الإمام الحاكم",    "hakim"),
    (re.compile(r'(?:وفي|في|ففي)\s+الدارقطني',                re.UNICODE), "الدارقطني",    "الإمام الدارقطني", "daraqutni"),
    # "رواه مسلم في الصحيح عن X قال: TEXT" — snippet AFTER the full phrase
    (re.compile(r'(?:رواه|أخرجه)\s+(?:الإمام\s+)?مسلم\s+في\s+الصحيح',     re.UNICODE), "صحيح مسلم",    "الإمام مسلم",      "muslim"),
    (re.compile(r'(?:رواه|أخرجه)\s+(?:الإمام\s+)?البخاري\s+في\s+الصحيح',  re.UNICODE), "صحيح البخاري", "الإمام البخاري",   "bukhari"),
    # "البخاري معلقًا في صحيحه" — علّقه + في صحيحه
    (re.compile(r'(?:علقه|علّقه)\s+(?:الإمام\s+)?البخاري[^:،؛\n]{0,60}:\s*', re.UNICODE), "صحيح البخاري", "الإمام البخاري", "bukhari"),
    # "ثبت في الصحيحين عن X قال: TEXT"
    (re.compile(r'ثبت\s+في\s+الصحيحين',                                    re.UNICODE), "الصحيحين",     "البخاري ومسلم",    "bukhari"),
    # "وفي البخاري من حديث X" — variant of direct reference
    (re.compile(r'(?:وفي|في)\s+البخاري\s+من\s+حديث',                       re.UNICODE), "صحيح البخاري", "الإمام البخاري",   "bukhari"),
    (re.compile(r'(?:وفي|في)\s+مسلم\s+من\s+حديث',                          re.UNICODE), "صحيح مسلم",    "الإمام مسلم",      "muslim"),
    # "وفي صحيحه" after explicit collection name context
    (re.compile(r'وفي\s+صحيح(?:ه|ه؟)',                                      re.UNICODE), "صحيح البخاري", "الإمام البخاري",   "bukhari"),
    # كما يصرح بهذا الحديث — rare but worth catching
]

# ── Pattern 4: Parenthetical attribution ─────────────────────────────────────
_PAREN_ATTR = re.compile(
    r'[(\[]\s*(?:رواه|أخرجه|متفق\s+عليه|خرّجه)\s*([^)\]]{0,60})[)\]]',
    re.UNICODE,
)

# ── Pattern 5: Standalone متفق عليه + block-style hadiths ─────────────────────
# "متفق عليه" can appear on its own line after a hadith block
_MUTTAFAQ = re.compile(r'متفق\s+عليه', re.UNICODE)

# Pattern 5b: Detect standalone collection names appearing on their own lines
# This handles cases like a hadith on one line followed by "الإمام مسلم" on the next
_COLLECTION_LINE = re.compile(
    r'\n\s*(?:الإمام\s+)?'
    r'(?:(?:صحيح\s+)?البخاري|(?:صحيح\s+)?مسلم|الصحيحين|متفق\s+عليه|'
    r'(?:سنن\s+)?(?:أبي?\s+داود|الترمذي|النسائي|ابن\s+ماج[هة]|أحمد)|'
    r'(?:مسند\s+)?أحمد|(?:موطأ?\s+)?مالك|البيهقي|الطبراني|الحاكم|الدارقطني)'
    r'(?:\s+|$)',
    re.UNICODE,
)


def _make(text: str, collection: str, collector: str, slug: str) -> HadithCitation:
    snippet = _clean(text)
    import urllib.parse
    return HadithCitation(
        text=snippet,
        collection=collection,
        collector=collector,
        # No bare collection link — sunnah.com will be enriched with sequence by hadith_verifier
        sunnah_url="",
        dorar_url=(_DORAR_SEARCH + urllib.parse.quote(snippet[:80], safe="")) if snippet else "",
    )


def _is_valid(snippet: str) -> bool:
    """A valid hadith snippet must have ≥10 chars AND ≥2 space-separated words."""
    return len(snippet) >= 10 and len(snippet.split()) >= 2


def _seen_key(slug: str, text: str) -> str:
    return f"{slug}::{text[:35]}"


def extract_citations(answer: str) -> list[HadithCitation]:
    """Extract all hadith citations; returns deduplicated list by position."""
    hits: list[tuple[int, HadithCitation]] = []
    seen: set[str] = set()

    def _add(pos: int, citation: HadithCitation) -> None:
        if not _is_valid(citation.text):
            return
        key = _seen_key(citation.sunnah_url, citation.text)
        if key not in seen:
            seen.add(key)
            hits.append((pos, citation))

    # 1. Prophetic-speech
    for m in _PROPHETIC.finditer(answer):
        raw = m.group(1)
        # Truncate at sentence boundary OR trigger verb, whichever comes first
        bnd = _BOUNDARY.search(raw)
        trg = _TRIGGER.search(raw)
        end = min(
            bnd.start() if bnd else len(raw),
            trg.start() if trg else len(raw),
            250,
        )
        body = _clean(raw[:end])
        if not _is_valid(body):
            continue
        # Look in a wide window (before + after match) for an explicit collection
        window = answer[max(0, m.start() - 300): m.end() + 200]
        info = _collection_for(window)
        if info:
            kw, collector, slug = info
            _add(m.start(), _make(body, kw, collector, slug))
        else:
            _add(m.start(), _make(body, "", "النبي ﷺ", "bukhari"))

    # 2. Trigger-verb scan
    # Handles: "رواه البخاري", "رواه الإمام مسلم", "أخرجه مسلم في صحيحه"
    for tm in _TRIGGER.finditer(answer):
        # Strip honorary title prefix ("الإمام", "الحافظ" etc.) before checking collection
        after_raw = answer[tm.end():]
        after = _IMAM_PREFIX.sub("", after_raw).strip()
        for kw, collector, slug in _COLLECTIONS:
            if after.startswith(kw) or kw in after[:50]:
                snippet = _snippet_before(answer, tm.start())
                _add(tm.start(), _make(snippet, kw, collector, slug))
                break

    # 3. Direct "في صحيح X" scan (all occurrences, not just first)
    # Also handles "في صحيحه" possessive when immediately preceded by a collection name
    for pattern, collection, collector, slug in _DIRECT:
        for m in pattern.finditer(answer):
            snippet = _snippet_after(answer, m.end())
            _add(m.start(), _make(snippet, collection, collector, slug))

    # 4. Parenthetical attribution
    for m in _PAREN_ATTR.finditer(answer):
        inner = m.group(0)
        info = _collection_for(inner)
        if not info and "متفق" in inner:
            info = ("متفق عليه", "البخاري ومسلم", "bukhari")
        if info:
            kw, collector, slug = info
            snippet = _snippet_before(answer, m.start())
            _add(m.start(), _make(snippet, kw, collector, slug))

    # 5. Standalone متفق عليه (all occurrences)
    for m in _MUTTAFAQ.finditer(answer):
        snippet = _snippet_before(answer, m.start())
        _add(m.start(), _make(snippet, "متفق عليه", "البخاري ومسلم", "bukhari"))

    # 6. Block-style: hadith on one line, collection name on next line
    # e.g.: "من أحدث في أمرنا هذا ما ليس منه فهو رد\nالإمام مسلم"
    for m in _COLLECTION_LINE.finditer(answer):
        line_text = m.group(0).strip()
        # Extract which collection this refers to
        info = _collection_for(line_text)
        if info:
            kw, collector, slug = info
            # Get the hadith text from previous line (before the newline)
            pre = answer[:m.start()]
            # Find the last sentence boundary before this line
            snippet = _snippet_before(answer, m.start())
            _add(m.start(), _make(snippet, kw, collector, slug))

    hits.sort(key=lambda x: x[0])
    return [h for _, h in hits]


# Legacy alias used by older callers
def extract_hadith_citations(answer: str) -> list[HadithCitation]:
    return extract_citations(answer)
