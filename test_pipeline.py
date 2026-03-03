"""
BinBaz Scraper — Test Pipeline
================================
Tests:
  1. Scrape 1 sample of each content type (fatwa, audio, article, speech, discussion, pearl, book)
  2. Download 1 Arabic book PDF
  3. Take the middle page and test 3 OCR methods side-by-side:
       A) PyMuPDF direct text extraction (baseline — expected to fail/garble on scanned PDFs)
       B) GOT-OCR2 local model (requires: pip install transformers torch tiktoken verovio)
       C) DeepSeek OCR public HuggingFace Space (free, needs internet)

Run:
  pip install scrapling PyMuPDF gradio_client Pillow tenacity requests
  python test_pipeline.py

Optional (for GOT-OCR2):
  pip install transformers torch tiktoken verovio
"""

import re, os, json, time, textwrap, traceback
from pathlib import Path
from datetime import datetime

# ── Output dirs ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
OUT_DIR    = BASE_DIR / "test_output"
PDF_DIR    = BASE_DIR / "files" / "pdfs"
IMG_DIR    = BASE_DIR / "files" / "page_images"
for d in [OUT_DIR, PDF_DIR, IMG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://binbaz.org.sa"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _fetcher():
    from scrapling.fetchers import Fetcher
    return Fetcher

def fetch(url: str):
    """Fetch a page with stealthy headers and return a Scrapling Response."""
    F = _fetcher()
    r = F.get(url, stealthy_headers=True, timeout=30)
    if r.status != 200:
        raise RuntimeError(f"HTTP {r.status} for {url}")
    time.sleep(0.4)   # polite delay
    return r

def clean(text: str | None) -> str:
    """Strip excessive whitespace from extracted text."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def encode_url(url: str) -> str:
    """
    Percent-encode any raw Unicode / space characters in a URL while
    preserving the scheme, host and existing %-sequences.
    Handles Arabic-character filenames and is idempotent on already-encoded URLs.
    """
    if not url:
        return ""
    from urllib.parse import quote, unquote, urlsplit, urlunsplit
    parts = urlsplit(url)
    # Decode first (handles already-%xx-encoded paths), then re-encode cleanly
    decoded_path = unquote(parts.path)
    encoded_path = quote(decoded_path, safe='/:@!$&\'()*+,;=')
    return urlunsplit((parts.scheme, parts.netloc, encoded_path,
                       parts.query, parts.fragment))


# Patterns that mark a trailing source-reference / publication note at the END
# of article / speech / discussion content.  Ordered from most specific to least.
_SOURCE_REF_PATTERNS = re.compile(
    r'('
    r'نشرت في\b'                             # نشرت في (published in ...)
    r'|\bنشر في\b'                           # نشر في (past tense, no ت)
    r'|محاضرة ألقيت\b'                       # محاضرة ألقيت (lecture delivered at)
    r'|خطبة ألقيت\b'                         # خطبة ألقيت (sermon delivered at)
    r'|(?<=[.،؛\]\)])\s*\[\d+\]\s+[\u0600-\u06FF]'  # [N] after punctuation — real footnote
    r'|\[\d+\]\s*[.،]?\s*\(?[\u0600-\u06FF]'   # [N] followed by optional ( then Arabic
    r'|\(?مجموع فتاوى'                        # مجموع فتاوى with or without leading (
    r')'
)

def extract_source_ref(text: str) -> tuple:
    """
    Split (body_text, source_ref) by detecting a trailing citation / footnote.
    Only scans the last 40% of text to avoid false positives on inline refs.
    Returns (text, "") if no ref found.
    """
    if not text:
        return text, ""
    cutoff = int(len(text) * 0.60)   # only look in the last 40%
    tail   = text[cutoff:]
    m = _SOURCE_REF_PATTERNS.search(tail)
    if m:
        split_pos = cutoff + m.start()
        return clean(text[:split_pos]), clean(text[split_pos:])
    return text, ""

def section_print(title: str):
    print("\n" + "═" * 70)
    print(f"  {title}")
    print("═" * 70)

def field_print(label: str, value: str | None, truncate: int = 300):
    value = clean(value) if value else "[NOT FOUND]"
    if len(value) > truncate:
        value = value[:truncate] + "…"
    print(f"  {label:20s}: {value}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — CONTENT SCRAPERS (1 sample each)
# ─────────────────────────────────────────────────────────────────────────────

# ─── Exact child sitemap URLs (confirmed from inventory scan) ────────────────
SITEMAP_MAP = {
    "fatwa":        "https://binbaz.org.sa/sitemaps/sitemap-fatwa-ar-1.xml",
    "audio":        "https://binbaz.org.sa/sitemaps/sitemap-audio-ar-1.xml",
    "audio_series": "https://binbaz.org.sa/sitemaps/sitemap-audio_series-ar-1.xml",
    "book":         "https://binbaz.org.sa/sitemaps/sitemap-book-ar-1.xml",
    "article":      "https://binbaz.org.sa/sitemaps/sitemap-article-ar-1.xml",
    "speech":       "https://binbaz.org.sa/sitemaps/sitemap-speech-ar-1.xml",
    "discussion":   "https://binbaz.org.sa/sitemaps/sitemap-discussion-ar-1.xml",
    "fiqhi":        "https://binbaz.org.sa/sitemaps/sitemap-fiqhi-ar-1.xml",
    "objective":    "https://binbaz.org.sa/sitemaps/sitemap-objective-ar-1.xml",
    # video intentionally omitted — we skip those
}

# ─── Hardcoded sample URLs from the inventory capture (instant, no sitemap needed) ─
SAMPLE_URLS = {
    "fatwa":      "https://binbaz.org.sa/fatwas/22447/%D9%88%D9%82%D8%AA-%D8%A7%D9%84%D8%B9%D9%85%D8%B1%D8%A9-%D8%A8%D8%B1%D9%85%D8%B6%D8%A7%D9%86-%D9%88%D8%AD%D9%83%D9%85-%D8%AA%D9%83%D8%B1%D8%A7%D8%B1%D9%87%D8%A7-%D9%88%D8%A7%D9%87%D8%AF%D8%A7%D9%89%D9%87%D8%A7",
    "pearl":      "https://binbaz.org.sa/pearls/229/%D9%84%D9%8A%D8%B3-%D9%84%D8%A7%D8%AD%D8%AF-%D8%A7%D9%86-%D9%8A%D9%81%D8%B3%D8%B1-%D9%83%D8%AA%D8%A7%D8%A8-%D8%A7%D9%84%D9%84%D9%87-%D8%A8%D8%AE%D9%84%D8%A7%D9%81-%D9%85%D8%A7-%D9%81%D8%B3%D8%B1%D9%87-%D8%A8%D9%87-%D8%B1%D8%B3%D9%88%D9%84%D9%87-%D8%B5%D9%84%D9%89-%D8%A7%D9%84%D9%84%D9%87-%D8%B9%D9%84%D9%8A%D9%87-%D9%88%D8%B3%D9%84%D9%85",
    "audio":      "https://binbaz.org.sa/audios/820/%D8%A7%D9%84%D8%AA%D9%88%D8%AD%D9%8A%D8%AF-%D9%81%D8%B6%D9%84%D9%87-%D9%88%D8%A7%D9%86%D9%88%D8%A7%D8%B9%D9%87-%D9%88%D8%AD%D9%83%D9%85%D9%87",
    # Hardcoded Arabic book from inventory — used for OCR comparison
    "book":       "https://binbaz.org.sa/books/216/%D8%B4%D8%B1%D8%AD-%D9%83%D8%AA%D8%A7%D8%A8-%D8%A7%D9%84%D8%AA%D9%88%D8%AD%D9%8A%D8%AF",
}
# article/speech/discussion pulled live from their sitemaps

def get_first_url_from_sitemap(sitemap_url: str) -> str | None:
    """Fetch a sitemap XML with raw requests (Scrapling parses XML as HTML, mangling <loc> tags)."""
    import requests
    try:
        resp = requests.get(sitemap_url, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        locs = re.findall(r'<loc>([^<]+)</loc>', resp.text)
        return locs[0] if locs else None
    except Exception as e:
        print(f"    [sitemap error] {e}")
        return None

def parse_sq_pairs(text: str) -> list:
    """
    Extract structured Q&A pairs from Arabic text containing
    inline س: (question) and ج: (answer) markers.

    Example input:
        س: هل يجوز...؟ ج: نعم يجوز. س: وماذا عن...؟ ج: لا مانع.

    Returns: [{"q": "هل يجوز...؟", "a": "نعم يجوز."}, ...]
    """
    pairs = []
    pattern = re.compile(
        r'\bس\s*[:：]\s*(.*?)\s*ج\s*[:：]\s*(.*?)(?=\s*\bس\s*[:：]|\Z)',
        re.DOTALL
    )
    for m in pattern.finditer(text):
        q = clean(m.group(1))
        a = clean(m.group(2))
        if q or a:
            pairs.append({"q": q, "a": a})
    return pairs

def scrape_fatwa(url: str) -> dict:
    r = fetch(url)
    title = clean(r.css("h1::text").get(""))

    # ── Question ──────────────────────────────────────────────────────────────
    # DOM: h2.article-title.article-title__question is OUTSIDE .article-content
    # Question text appears in one of several DOM locations (tried in order):
    #   A) h2 → B) sibling <p> → C) sibling <div> → D) inside .article-content
    #   (No title fallback — empty question = extraction bug to investigate)
    _strip_q = lambda t: re.sub(r'^(?:السؤال|س)\s*[：:]?\s*', '', t).strip()

    question = ""
    q_el = r.css("h2.article-title__question")
    if q_el:
        question = _strip_q(clean(
            " ".join(q_el.css(":not(script):not(style)::text").getall())
        ))
    if not question:
        sibling_ps = r.css("article.fatwa > p")
        raw = clean(" ".join(
            clean(" ".join(el.css(":not(script):not(style)::text").getall()))
            for el in sibling_ps
        ))
        question = _strip_q(raw)
    if not question:
        for el in r.css("article.fatwa > div"):
            cls = " ".join(el.css("::attr(class)").getall())
            if any(skip in cls for skip in ("article-content", "row", "audio")):
                continue
            txt = clean(" ".join(el.css(":not(script):not(style)::text").getall()))
            txt = _strip_q(txt)
            if txt:
                question = txt
                break
    if not question:
        content_parts = []
        for el in r.css(".article-content > *:not(.footnotes)"):
            txt = clean(" ".join(el.css(":not(script):not(style)::text").getall()))
            if re.match(r'^(?:الجواب|ج)\s*[：:]', txt):
                break
            content_parts.append(txt)
        if content_parts:
            question = _strip_q(" ".join(content_parts))
    # No title fallback — leave empty so missing questions are visible
    if not question:
        import logging
        logging.warning(f"No question extracted from DOM for {url}")

    # ── Source reference (footnotes) ──────────────────────────────────────────
    # DOM: .article-content .footnotes li contains publication refs like
    # "مجموع فتاوى ابن باز (1/ 54)."
    footnote_items = [
        clean(" ".join(el.css(":not(script):not(style)::text").getall()))
        for el in r.css(".article-content .footnotes li")
    ]
    source_ref = "  ".join(p for p in footnote_items if p)

    # ── Answer body (exclude .footnotes) ─────────────────────────────────────
    # First try child elements (covers most fatwas with <p> tags)
    answer_text = clean(" ".join(
        clean(" ".join(el.css(":not(script):not(style)::text").getall()))
        for el in r.css(".article-content > *:not(.footnotes)")
    ))
    # Fallback: some short fatwas have answer as a bare text node directly inside
    # .article-content with no <p> wrapper — child-element selector misses those.
    if not answer_text:
        answer_text = clean(" ".join(r.css(".article-content::text").getall()))
    answer_stripped = re.sub(r'^(?:الجواب|ج)\s*[：:]?\s*', '', answer_text).strip()
    # Some fatwas have nested "الجواب: ج:" — strip repeatedly
    while re.match(r'^(?:الجواب|ج)\s*[：:]?\s*', answer_stripped):
        answer_stripped = re.sub(r'^(?:الجواب|ج)\s*[：:]?\s*', '', answer_stripped).strip()

    # Strip any trailing inline source ref that leaks through from the last <p>
    answer_stripped, _inline_ref = extract_source_ref(answer_stripped)
    if not source_ref and _inline_ref:
        source_ref = _inline_ref

    # Split into direct reply + nested س/ج follow-up pairs
    first_followup = re.search(r'\bس\s*[：:]', answer_stripped)
    if first_followup:
        answer_direct = clean(answer_stripped[:first_followup.start()])
        nested_qa     = parse_sq_pairs(answer_stripped[first_followup.start():])
    else:
        answer_direct = answer_stripped
        nested_qa     = []

    # ── Categories ────────────────────────────────────────────────────────────
    # KEY FIX: Use pure CSS descendant selector to scope to the MAIN article
    # category block only.
    # DOM hierarchy:
    #   .utility__flex--auto > .categories > .categories__item  ← MAIN (what we want)
    #   .box__body__element.fatwa > .categories > .categories__item ← related fatwa cats (skip)
    # Scrapling has no .root; use descendant CSS selector instead.
    raw_cats = [
        clean(" ".join(el.css("*::text").getall()))
        for el in r.css(".utility__flex--auto .categories__item")
    ]
    categories = list(dict.fromkeys(c for c in raw_cats if c))

    # ── Related fatwas (explicit graph edges for RAG) ────────────────────────
    # DOM: .box__body__element.fatwa contains links to related fatwas.
    # We store [{url, title}] for graph-traversal expansion during retrieval.
    related = []
    for box in r.css(".box__body__element.fatwa"):
        a_tags = box.css("a[href*='/fatwas/']")
        if not a_tags:
            continue
        a = a_tags[0]
        href   = a.css("::attr(href)").get("") or ""
        rurl   = (BASE_URL.rstrip("/") + href) if href.startswith("/") else href
        rtitle = clean(" ".join(a.css("::text").getall()))
        if rurl and rtitle:
            related.append({"url": rurl, "title": rtitle})

    audio_url = r.css(".download-btn::attr(href)").get("") or ""

    # Numeric ID extracted from URL (used for graph adjacency at retrieval time)
    _id_m = re.search(r'/fatwas/(\d+)/', url)
    fatwa_id = int(_id_m.group(1)) if _id_m else None

    # Full embedding text: question + answer body
    full_text = (question + " " + answer_stripped).strip() if question else answer_stripped

    return {
        "content_type":  "fatwa",
        "fatwa_id":      fatwa_id,
        "url":           url,
        "title":         title,
        "question":      question,
        "answer_direct": answer_direct,
        "nested_qa":     nested_qa,
        "answer":        answer_stripped,
        "source_ref":    source_ref,
        "text":          full_text,
        "categories":    categories,
        "related":       related,
        "related_ids":   [
            int(m.group(1))
            for rel in related
            for m in [re.search(r'/fatwas/(\d+)/', rel["url"])]
            if m
        ],
        "audio_url":     encode_url(audio_url) if audio_url.endswith(".mp3") else "",
        "scraped_at":    datetime.now().isoformat(),
    }


def scrape_audio_page(url: str) -> dict:
    """
    Selectors (confirmed live):
      Title      : h1
      Transcript : .article-content  ← FULL written transcript already on page!
                   Structure: [lecture text] ... الأسئلة: [Q&A pairs]
      Audio link : .download-btn[href] → .mp3

    We split the transcript into two parts for richer RAG indexing:
      lecture_text  — the main scholarly lecture
      qa_text       — the follow-up Q&A session (starts after الأسئلة:)
    """
    r = fetch(url)
    title      = clean(r.css("h1::text").get(""))
    transcript = clean(" ".join(r.css(".article-content :not(script):not(style)::text").getall()))
    audio_url  = r.css(".download-btn::attr(href)").get("")

    # Deduplicate categories (same issue as fatwa)
    raw_cats   = [clean(" ".join(el.css("*::text").getall())) for el in r.css(".categories__item")]
    categories = list(dict.fromkeys(c for c in raw_cats if c))

    # Split transcript into lecture and Q&A section
    QA_MARKER = "الأسئلة"
    if QA_MARKER in transcript:
        idx = transcript.index(QA_MARKER)
        lecture_text = clean(transcript[:idx])
        qa_text      = clean(transcript[idx:])
    else:
        lecture_text = transcript
        qa_text      = ""

    # Parse the Q&A session into structured س/ج pairs for fine-grained RAG
    qa_pairs = parse_sq_pairs(qa_text) if qa_text else []

    return {
        "content_type":  "audio",
        "url":           url,
        "title":         title,
        "transcript":    transcript,      # full transcript (for reference)
        "lecture_text":  lecture_text,    # main lecture part  (embedding chunk 1)
        "qa_text":       qa_text,         # full Q&A session text  (embedding chunk 2)
        "qa_pairs":      qa_pairs,        # structured [{q, a}] list
        "text":          transcript,      # used for single-doc embedding (full)
        "categories":    categories,
        "audio_url":     encode_url(audio_url) if ".mp3" in audio_url else "",
        "scraped_at":    datetime.now().isoformat(),
    }


def scrape_text_page(url: str, content_type: str) -> dict:
    """
    Generic scraper for article / speech / discussion / pearl.
    Selectors: h1 for title, .article-content for body.
    Extracts trailing publication / footnote refs into source_ref field.
    """
    r = fetch(url)
    title  = clean(r.css("h1::text").get(""))
    raw_body = clean(" ".join(r.css(".article-content :not(script):not(style)::text").getall()))
    body, source_ref = extract_source_ref(raw_body)
    # Deduplicate categories (HTML may repeat the same item multiple times)
    raw_cats   = [clean(" ".join(el.css("*::text").getall())) for el in r.css(".categories__item")]
    cats       = list(dict.fromkeys(c for c in raw_cats if c))
    date   = clean(r.css("time::attr(datetime)").get("") or r.css(".date::text").get(""))

    return {
        "content_type": content_type,
        "url":          url,
        "title":        title,
        "text":         body,
        "source_ref":   source_ref,   # publication / footnote reference
        "categories":   cats,
        "date":         date,
        "scraped_at":   datetime.now().isoformat(),
    }


def scrape_book_page(url: str) -> dict | None:
    """
    Selectors (confirmed live):
      Title    : h1
      PDF link : a[href*='/pdf/']

    Returns None if this is a translated (non-Arabic) book.
    """
    # Language filter
    TRANSLATION_SUFFIXES = {
        "فرنسي","إنجليزي","هندي","تركي","أردو","سنهالي","مليالم","إندونيسي",
        "بنغالي","ألماني","إسباني","روسي","صومالي","سواحيلي","أمهرية","هوسا",
        "ملايو","تيغرينيا","إيطالي","برتغالي","فارسي","بوسنوي","ألباني",
    }
    r     = fetch(url)
    title = clean(r.css("h1::text").get(""))

    # Skip translated books
    m = re.search(r'\s+-\s+(\S+)$', title)
    if m and m.group(1) in TRANSLATION_SUFFIXES:
        print(f"  [SKIP] Translated book: {title}")
        return None

    pdf_href = r.css("a[href*='/pdf/']::attr(href)").get("")
    pdf_url  = (BASE_URL + pdf_href) if pdf_href.startswith("/") else pdf_href

    return {
        "content_type": "book",
        "url":          url,
        "title":        title,
        "pdf_url":      pdf_url,
        "scraped_at":   datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — PDF OCR COMPARISON
# ─────────────────────────────────────────────────────────────────────────────

def download_pdf(pdf_url: str, book_id: str) -> Path:
    import requests
    dest = PDF_DIR / f"{book_id}.pdf"
    if dest.exists():
        print(f"  [CACHE] PDF already downloaded: {dest}")
        return dest
    print(f"  Downloading PDF: {pdf_url}")
    resp = requests.get(pdf_url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(65536):
            f.write(chunk)
    print(f"  Saved to: {dest}")
    return dest


def render_page_as_image(pdf_path: Path, page_index: int) -> Path:
    """Render a PDF page to a JPEG image using PyMuPDF."""
    import fitz
    doc    = fitz.open(str(pdf_path))
    page   = doc[page_index]
    pix    = page.get_pixmap(dpi=200)
    img_path = IMG_DIR / f"{pdf_path.stem}_page{page_index}.jpg"
    pix.save(str(img_path))
    print(f"  Rendered page {page_index + 1} → {img_path}")
    return img_path


def get_page_count(pdf_path: Path) -> int:
    import fitz
    doc = fitz.open(str(pdf_path))
    return len(doc)


# ── Method A: PyMuPDF direct text extraction ──────────────────────────────────
def ocr_pymupdf(pdf_path: Path, page_index: int) -> str:
    """Baseline: try to extract digital text. Expected to fail on scanned PDFs."""
    import fitz
    doc  = fitz.open(str(pdf_path))
    page = doc[page_index]
    text = page.get_text("text").strip()
    return text if text else "[PyMuPDF returned empty — likely scanned PDF]"


# ── Method B: GOT-OCR2 local model ──────────────────────────────────────────
def ocr_got(image_path: Path) -> str:
    """
    Requires: pip install transformers torch tiktoken verovio
    Uses stepfun-ai/GOT-OCR2_0 (580M params) — tiny, Arabic-capable.
    Downloads ~1.5GB model on first run.
    """
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer

        print("  [GOT-OCR] Loading model (downloads ~1.5GB on first run)…")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tokenizer = AutoTokenizer.from_pretrained(
            "stepfun-ai/GOT-OCR2_0", trust_remote_code=True
        )
        model = AutoModel.from_pretrained(
            "stepfun-ai/GOT-OCR2_0",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            device_map=device,
            use_safetensors=True,
        ).eval()

        result = model.chat(tokenizer, str(image_path), ocr_type="ocr")
        return result

    except ImportError:
        return "[GOT-OCR SKIPPED] Install: pip install transformers torch tiktoken verovio"
    except Exception as e:
        return f"[GOT-OCR ERROR] {e}"


# ── Method C: DeepSeek OCR public HuggingFace Space ─────────────────────────
def ocr_deepseek_space(image_path: Path) -> str:
    """
    Calls public Space: khang119966/DeepSeek-OCR-DEMO
    Free, no auth needed. Rate-limited on heavy use.
    """
    try:
        from gradio_client import Client, handle_file

        print("  [DeepSeek] Connecting to HuggingFace Space…")
        client = Client("khang119966/DeepSeek-OCR-DEMO")
        result = client.predict(
            image=handle_file(str(image_path)),
            model_size="Gundam (Recommended)",
            task_type="📄 Convert to Markdown",
            ref_text="",
            api_name="/process_ocr_task",
        )
        raw = result[0]

        # Strip DeepSeek's internal bounding-box tokens
        clean_text = re.sub(r'<\|ref\|>.*?<\|/ref\|>', '', raw)
        clean_text = re.sub(r'<\|det\|>.*?<\|/det\|>', '', clean_text)
        return clean_text.strip()

    except Exception as e:
        return f"[DeepSeek Space ERROR] {e}"


def compare_ocr(pdf_path: Path, page_index: int):
    """Run all 3 OCR methods on the same page and print results."""
    section_print(f"OCR COMPARISON — page {page_index + 1} of {pdf_path.name}")

    # Render page to image (needed for GOT + DeepSeek)
    img_path = render_page_as_image(pdf_path, page_index)

    # --- Method A ---
    print("\n  ── A) PyMuPDF direct text extraction (baseline) ──")
    try:
        result_a = ocr_pymupdf(pdf_path, page_index)
        print(textwrap.fill(result_a[:800], width=80, initial_indent="  ", subsequent_indent="  "))
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- Method B ---
    print("\n  ── B) GOT-OCR2 (local 580M model) ──")
    try:
        result_b = ocr_got(img_path)
        print(textwrap.fill(result_b[:800], width=80, initial_indent="  ", subsequent_indent="  "))
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- Method C ---
    print("\n  ── C) DeepSeek OCR HuggingFace Space ──")
    try:
        result_c = ocr_deepseek_space(img_path)
        print(textwrap.fill(result_c[:800], width=80, initial_indent="  ", subsequent_indent="  "))
    except Exception as e:
        print(f"  ERROR: {e}")

    # Save all results to JSON
    results = {
        "pdf":        str(pdf_path),
        "page_index": page_index,
        "image":      str(img_path),
        "pymupdf":    result_a,
        "got_ocr":    result_b,
        "deepseek":   result_c,
    }
    out = OUT_DIR / f"ocr_comparison_{pdf_path.stem}_p{page_index}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Full results saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — MAIN TEST RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def main():
    all_results = {}

    # ── Use hardcoded samples + live sitemap for remaining types ─────────────
    section_print("STEP 0 — Resolving sample URLs")

    discovered = dict(SAMPLE_URLS)  # start with hardcoded fast URLs

    # Pull first URL from sitemaps for types not in hardcoded list
    for ctype in ["article", "speech", "discussion"]:
        try:
            sitemap_url = SITEMAP_MAP[ctype]
            print(f"  [{ctype}] Fetching first URL from: {sitemap_url}")
            sample_url = get_first_url_from_sitemap(sitemap_url)
            if sample_url:
                discovered[ctype] = sample_url
                print(f"  [{ctype}] → {sample_url}")
            else:
                print(f"  [{ctype}] Sitemap returned no URLs")
        except Exception as e:
            print(f"  [{ctype}] ERROR: {e}")

    print(f"\n  Discovered {len(discovered)} content type sample URLs.")

    # ── Scrape 1 of each ─────────────────────────────────────────────────────

    # FATWA
    if "fatwa" in discovered:
        section_print(f"FATWA — {discovered['fatwa']}")
        try:
            result = scrape_fatwa(discovered["fatwa"])
            field_print("Title",         result["title"])
            field_print("Question",      result["question"])
            field_print("Answer Direct", result["answer_direct"])
            field_print("Nested QA #",   str(len(result["nested_qa"])) + " pairs")
            if result["nested_qa"]:
                for i, pair in enumerate(result["nested_qa"][:3], 1):  # show first 3
                    field_print(f"  NQ[{i}] Q", pair["q"][:100])
                    field_print(f"  NQ[{i}] A", pair["a"][:100])
            field_print("Categories",    str(result["categories"]))
            field_print("Audio URL",     result["audio_url"])
            all_results["fatwa"] = result
        except Exception as e:
            print(f"  ERROR: {e}"); traceback.print_exc()

    # AUDIO (has on-page transcript)
    if "audio" in discovered:
        section_print(f"AUDIO (on-page transcript) — {discovered['audio']}")
        try:
            result = scrape_audio_page(discovered["audio"])
            field_print("Title",         result["title"])
            field_print("Lecture (start)",result["lecture_text"][:200] if result["lecture_text"] else "")
            field_print("QA pairs #",    str(len(result["qa_pairs"])) + " pairs")
            if result["qa_pairs"]:
                for i, pair in enumerate(result["qa_pairs"][:3], 1):
                    field_print(f"  QP[{i}] Q", pair["q"][:100])
                    field_print(f"  QP[{i}] A", pair["a"][:100])
            field_print("Audio URL",     result["audio_url"])
            field_print("Has transcript?","YES ✓" if result["transcript"] else "NO ✗")
            all_results["audio"] = result
        except Exception as e:
            print(f"  ERROR: {e}"); traceback.print_exc()

    # ARTICLE, SPEECH, DISCUSSION
    for ctype in ["article", "speech", "discussion"]:
        if ctype in discovered:
            section_print(f"{ctype.upper()} — {discovered[ctype]}")
            try:
                result = scrape_text_page(discovered[ctype], ctype)
                field_print("Title",      result["title"])
                field_print("Body",       result["text"])
                field_print("Source Ref", result.get("source_ref", "") or "[none]")
                field_print("Date",       result.get("date", ""))
                all_results[ctype] = result
            except Exception as e:
                print(f"  ERROR: {e}"); traceback.print_exc()

    # PEARL (direct URL from inventory)
    if "pearl" in discovered:
        section_print(f"PEARL — {discovered['pearl']}")
        try:
            result = scrape_text_page(discovered["pearl"], "pearl")
            field_print("Title", result["title"])
            field_print("Text",  result["text"])
            all_results["pearl"] = result
        except Exception as e:
            print(f"  ERROR: {e}"); traceback.print_exc()

    # BOOK — find an Arabic book (no language suffix), scrape it
    book_result = None
    if "book" in discovered:
        section_print(f"BOOK — {discovered['book']}")
        try:
            result = scrape_book_page(discovered["book"])
            if result:
                field_print("Title",   result["title"])
                field_print("PDF URL", result["pdf_url"])
                all_results["book"] = result
                book_result = result
            else:
                print("  [SKIP] Book was translated — trying next from sitemap...")
                locs = get_first_url_from_sitemap(SITEMAP_MAP["book"])
                # locs is just one URL here; for a real fallback we'd parse all
                print("  Tip: hardcode a different book URL in SAMPLE_URLS['book']")
        except Exception as e:
            print(f"  ERROR: {e}"); traceback.print_exc()

    # ── Save scraping results ─────────────────────────────────────────────────
    out_file = OUT_DIR / "scrape_results.json"
    out_file.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    section_print(f"ALL DONE — {out_file}")
    print(f"  Scraped {len(all_results)} content type(s) successfully.")


if __name__ == "__main__":
    main()
