"""
BinBaz Full Production Scraper
================================
Scrapes ALL content from binbaz.org.sa using the validated scrapers from test_pipeline.py.

Content types and estimated counts:
  fatwa      : 24,601
  audio      : 3,475
  book       : 402    (skips translated books)
  speech     : 298
  article    : 169
  discussion : 133
  fiqhi      : 174    (same scraper as article)
  objective  : 55     (same scraper as article)
  Total      ≈ 29,307

Output:
  output/<type>.jsonl   — one JSON object per line (append-mode, resumable)
  output/errors.jsonl   — failed URLs with error messages
  output/progress.json  — live counters per content type

Resumability:
  Already-scraped URLs tracked via per-type seen sets loaded from existing .jsonl
  files at startup.  Re-running the script safely skips completed work.

Usage:
  pip install scrapling requests
  python run.py [--workers N] [--delay SECONDS]
"""

import re, os, json, sys, time, traceback, argparse, threading
from pathlib import Path
from datetime import datetime, timedelta
from queue import Queue, Empty
from urllib.parse import quote, unquote, urlsplit, urlunsplit

# ── Directories ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
OUT_DIR  = BASE_DIR / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Force UTF-8 output on Windows so box-drawing / Arabic chars print correctly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://binbaz.org.sa"

# ── Sitemap map ───────────────────────────────────────────────────────────────
SITEMAP_MAP = {
    "fatwa":      "https://binbaz.org.sa/sitemaps/sitemap-fatwa-ar-1.xml",
    "audio":      "https://binbaz.org.sa/sitemaps/sitemap-audio-ar-1.xml",
    "book":       "https://binbaz.org.sa/sitemaps/sitemap-book-ar-1.xml",
    "article":    "https://binbaz.org.sa/sitemaps/sitemap-article-ar-1.xml",
    "speech":     "https://binbaz.org.sa/sitemaps/sitemap-speech-ar-1.xml",
    "discussion": "https://binbaz.org.sa/sitemaps/sitemap-discussion-ar-1.xml",
    # fiqhi / objective removed: their sitemaps point to /categories/ listing
    # pages which have no .article-content — 100% empty text, useless data.
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def clean(text) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def encode_url(url: str) -> str:
    """Percent-encode raw Unicode / spaces in URL paths (idempotent)."""
    if not url:
        return ""
    parts = urlsplit(url)
    decoded_path = unquote(parts.path)
    encoded_path = quote(decoded_path, safe='/:@!$&\'()*+,;=')
    return urlunsplit((parts.scheme, parts.netloc, encoded_path, parts.query, parts.fragment))

_SOURCE_REF_PATTERNS = re.compile(
    r'('
    r'نشرت في\b'
    r'|\bنشر في\b'                              # نشر في (past tense, no ت)
    r'|محاضرة ألقيت\b'
    r'|خطبة ألقيت\b'
    r'|(?<=[.،؛\]\)])\s*\[\d+\]\s+[\u0600-\u06FF]'
    r'|\[\d+\]\s*[.،]?\s*\(?[\u0600-\u06FF]'   # [N] followed by optional ( then Arabic
    r'|\(?مجموع فتاوى'                        # مجموع فتاوى with or without leading (
    r')'
)

def extract_source_ref(text: str) -> tuple:
    if not text:
        return text, ""
    cutoff = int(len(text) * 0.60)
    tail = text[cutoff:]
    m = _SOURCE_REF_PATTERNS.search(tail)
    if m:
        split_pos = cutoff + m.start()
        return clean(text[:split_pos]), clean(text[split_pos:])
    return text, ""

def parse_sq_pairs(text: str) -> list:
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

# ── Fetcher ───────────────────────────────────────────────────────────────────
_fetch_lock = threading.Lock()
_DELAY = 0.5   # overridden by args.delay in main()

def fetch(url: str):
    from scrapling.fetchers import Fetcher
    r = Fetcher.get(url, stealthy_headers=True, timeout=30)
    if r.status != 200:
        raise RuntimeError(f"HTTP {r.status}")
    time.sleep(_DELAY)
    return r

def fetch_sitemap_urls(sitemap_url: str) -> list:
    """Fetch all <loc> URLs from a sitemap XML."""
    import requests
    resp = requests.get(sitemap_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return re.findall(r'<loc>([^<]+)</loc>', resp.text)

# ─────────────────────────────────────────────────────────────────────────────
# SCRAPERS (identical logic to test_pipeline.py)
# ─────────────────────────────────────────────────────────────────────────────

TRANSLATION_SUFFIXES = {
    "فرنسي","إنجليزي","هندي","تركي","أردو","سنهالي","مليالم","إندونيسي",
    "بنغالي","ألماني","إسباني","روسي","صومالي","سواحيلي","أمهرية","هوسا",
    "ملايو","تيغرينيا","إيطالي","برتغالي","فارسي","بوسنوي","ألباني",
}

def scrape_fatwa(url: str) -> dict:
    r = fetch(url)
    title = clean(r.css("h1::text").get(""))

    # ── Question ──────────────────────────────────────────────────────────────
    # Question text appears in one of several DOM locations (tried in order):
    #   A) h2.article-title__question — contains question directly
    #   B) article.fatwa > p — sibling <p> elements (after label-only h2)
    #   C) article.fatwa > div (not .article-content/.row/.audio) — sibling <div>
    #   D) Inside .article-content before الجواب — mixed Q&A in body
    #   (No title fallback — empty question = extraction bug to investigate)
    _strip_q = lambda t: re.sub(r'^(?:السؤال|س)\s*[：:]?\s*', '', t).strip()

    question = ""
    # A) h2 text
    q_el = r.css("h2.article-title__question")
    if q_el:
        question = _strip_q(clean(
            " ".join(q_el.css(":not(script):not(style)::text").getall())
        ))
    # B) sibling <p> elements
    if not question:
        sibling_ps = r.css("article.fatwa > p")
        raw = clean(" ".join(
            clean(" ".join(el.css(":not(script):not(style)::text").getall()))
            for el in sibling_ps
        ))
        question = _strip_q(raw)
    # C) sibling <div> elements (not article-content/row/audio)
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
    # D) Inside .article-content: question text before الجواب/ج: marker
    if not question:
        content_parts = []
        for el in r.css(".article-content > *:not(.footnotes)"):
            txt = clean(" ".join(el.css(":not(script):not(style)::text").getall()))
            if re.match(r'^(?:الجواب|ج)\s*[：:]', txt):
                break
            content_parts.append(txt)
        if content_parts:
            raw = " ".join(content_parts)
            question = _strip_q(raw)
    # E) No title fallback — leave empty so missing questions are visible
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

    # Strip any trailing inline source ref (e.g. "[1] . مجموع فتاوى ابن باز (1/49)")
    # that leaks through from the last <p> — source_ref is already captured from
    # .footnotes li above, so we don't need it duplicated in the answer body.
    answer_stripped, _inline_ref = extract_source_ref(answer_stripped)
    if not source_ref and _inline_ref:
        source_ref = _inline_ref  # use inline ref if no footnotes section found

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


def scrape_audio(url: str) -> dict:
    r = fetch(url)
    title      = clean(r.css("h1::text").get(""))
    transcript = clean(" ".join(r.css(".article-content :not(script):not(style)::text").getall()))
    audio_url  = r.css(".download-btn::attr(href)").get("")
    raw_cats   = [clean(" ".join(el.css("*::text").getall())) for el in r.css(".utility__flex--auto .categories__item")]
    categories = list(dict.fromkeys(c for c in raw_cats if c))

    QA_MARKER = "الأسئلة"
    if QA_MARKER in transcript:
        idx = transcript.index(QA_MARKER)
        lecture_text = clean(transcript[:idx])
        qa_text      = clean(transcript[idx:])
    else:
        lecture_text = transcript
        qa_text      = ""

    qa_pairs = parse_sq_pairs(qa_text) if qa_text else []

    return {
        "content_type": "audio",
        "url":          url,
        "title":        title,
        "transcript":   transcript,
        "lecture_text": lecture_text,
        "qa_text":      qa_text,
        "qa_pairs":     qa_pairs,
        "text":         transcript,
        "categories":   categories,
        "audio_url":    encode_url(audio_url) if ".mp3" in audio_url else "",
        "scraped_at":   datetime.now().isoformat(),
    }

def scrape_text(url: str, content_type: str) -> dict:
    r = fetch(url)
    title    = clean(r.css("h1::text").get(""))
    raw_body = clean(" ".join(r.css(".article-content :not(script):not(style)::text").getall()))
    body, source_ref = extract_source_ref(raw_body)
    raw_cats = [clean(" ".join(el.css("*::text").getall())) for el in r.css(".utility__flex--auto .categories__item")]
    cats     = list(dict.fromkeys(c for c in raw_cats if c))
    date     = clean(r.css("time::attr(datetime)").get("") or r.css(".date::text").get(""))
    return {
        "content_type": content_type,
        "url":          url,
        "title":        title,
        "text":         body,
        "source_ref":   source_ref,
        "categories":   cats,
        "date":         date,
        "scraped_at":   datetime.now().isoformat(),
    }

def scrape_book(url: str) -> dict | None:
    r     = fetch(url)
    title = clean(r.css("h1::text").get(""))
    m = re.search(r'\s+-\s+(\S+)$', title)
    if m and m.group(1) in TRANSLATION_SUFFIXES:
        return None   # skip translated book
    pdf_href = r.css("a[href*='/pdf/']::attr(href)").get("")
    pdf_url  = (BASE_URL + pdf_href) if pdf_href.startswith("/") else pdf_href
    return {
        "content_type": "book",
        "url":          url,
        "title":        title,
        "pdf_url":      pdf_url,
        "scraped_at":   datetime.now().isoformat(),
    }

# Dispatch table: content_type → scraper function
SCRAPERS = {
    "fatwa":      scrape_fatwa,
    "audio":      scrape_audio,
    "book":       scrape_book,
    "article":    lambda u: scrape_text(u, "article"),
    "speech":     lambda u: scrape_text(u, "speech"),
    "discussion": lambda u: scrape_text(u, "discussion"),
}

# ─────────────────────────────────────────────────────────────────────────────
# PROGRESS & OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

class Stats:
    def __init__(self, totals: dict):
        self._lock    = threading.Lock()
        self.done     = {k: 0 for k in totals}
        self.skipped  = {k: 0 for k in totals}
        self.errors   = {k: 0 for k in totals}
        self.totals   = totals
        self.start    = time.time()

    def inc(self, ctype: str, kind: str):
        with self._lock:
            getattr(self, kind)[ctype] += 1

    def summary(self) -> str:
        elapsed = time.time() - self.start
        done_total = sum(self.done.values())
        grand_total = sum(self.totals.values())
        pct  = done_total / grand_total * 100 if grand_total else 0
        rate = done_total / elapsed if elapsed > 0 else 0
        eta  = ""
        if rate > 0 and done_total < grand_total:
            secs = (grand_total - done_total) / rate
            eta  = f"  ETA: {str(timedelta(seconds=int(secs)))}"
        lines = [
            f"\n{'─'*68}",
            f"  Progress: {done_total}/{grand_total} ({pct:.1f}%)  "
            f"Rate: {rate:.1f} doc/s{eta}",
            f"{'─'*68}",
        ]
        for ct in self.totals:
            d = self.done[ct]
            t = self.totals[ct]
            e = self.errors[ct]
            s = self.skipped[ct]
            lines.append(f"  {ct:12s}: {d:5d}/{t:5d}  err:{e:4d}  skip:{s:4d}")
        return "\n".join(lines)


_out_locks: dict[str, threading.Lock] = {
    ctype: threading.Lock()
    for ctype in ["fatwa", "audio", "book", "article", "speech", "discussion", "errors"]
}

def _out_lock(ctype: str) -> threading.Lock:
    return _out_locks.get(ctype, _out_locks["errors"])

def write_record(ctype: str, record: dict):
    path = OUT_DIR / f"{ctype}.jsonl"
    with _out_lock(ctype):
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

def write_error(ctype: str, url: str, err: str):
    rec = {"content_type": ctype, "url": url, "error": err, "at": datetime.now().isoformat()}
    with _out_lock("errors"):
        with open(OUT_DIR / "errors.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def load_seen_urls(ctype: str) -> set:
    """Load already-scraped URLs from the JSONL file for this content type."""
    seen = set()
    path = OUT_DIR / f"{ctype}.jsonl"
    if not path.exists():
        return seen
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if "url" in obj:
                    seen.add(obj["url"])
            except json.JSONDecodeError:
                pass
    return seen

# ─────────────────────────────────────────────────────────────────────────────
# WORKER
# ─────────────────────────────────────────────────────────────────────────────

def worker(q: Queue, stats: Stats, print_lock: threading.Lock):
    while True:
        try:
            ctype, url = q.get(timeout=5)
        except Empty:
            break
        try:
            fn = SCRAPERS[ctype]
            record = fn(url)
            if record is None:
                # scraper returned None (e.g. translated book)
                stats.inc(ctype, "skipped")
            else:
                write_record(ctype, record)
                stats.inc(ctype, "done")
        except Exception as e:
            err_msg = str(e)
            write_error(ctype, url, err_msg)
            stats.inc(ctype, "errors")
        finally:
            q.task_done()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BinBaz full scraper")
    parser.add_argument("--workers", type=int, default=3,
                        help="Number of parallel fetch threads (default: 3)")
    parser.add_argument("--delay",   type=float, default=0.5,
                        help="Seconds to sleep after each request (default: 0.5)")
    parser.add_argument("--types",   nargs="*", default=list(SITEMAP_MAP.keys()),
                        help="Content types to scrape (default: all)")
    args = parser.parse_args()

    global _DELAY
    _DELAY = args.delay

    print(f"\n{'═'*68}")
    print(f"  BinBaz Production Scraper  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Workers: {args.workers}   Delay: {args.delay}s   Output: {OUT_DIR}")
    print(f"{'═'*68}\n")

    # ── Step 1: fetch all sitemaps, build URL lists ────────────────────────────
    all_urls: dict[str, list] = {}
    for ctype in args.types:
        sitemap = SITEMAP_MAP[ctype]
        print(f"  [sitemap] Fetching {ctype}: {sitemap}")
        try:
            urls = fetch_sitemap_urls(sitemap)
            all_urls[ctype] = urls
            print(f"            → {len(urls)} URLs found")
        except Exception as e:
            print(f"            ERROR: {e}")
            all_urls[ctype] = []

    # ── Step 2: load already-done URLs (resumability) ─────────────────────────
    print("\n  Loading existing output for resumability...")
    seen: dict[str, set] = {}
    for ctype in args.types:
        seen[ctype] = load_seen_urls(ctype)
        if seen[ctype]:
            print(f"    {ctype:12s}: {len(seen[ctype])} already done — will skip")

    # ── Step 3: build queue (only pending URLs) ────────────────────────────────
    q: Queue = Queue()
    totals: dict[str, int] = {}
    for ctype in args.types:
        pending = [u for u in all_urls[ctype] if u not in seen[ctype]]
        totals[ctype] = len(all_urls[ctype])
        for url in pending:
            q.put((ctype, url))
        print(f"  {ctype:12s}: {len(pending)} pending  ({len(seen[ctype])} skipped)")

    total_pending = sum(
        len([u for u in all_urls[ct] if u not in seen[ct]])
        for ct in args.types
    )
    print(f"\n  Total pending: {total_pending:,} pages\n")
    if total_pending == 0:
        print("  Nothing to do — all URLs already scraped!")
        return

    # ── Step 4: spawn workers ──────────────────────────────────────────────────
    stats = Stats(totals)
    print_lock = threading.Lock()

    threads = []
    for _ in range(args.workers):
        t = threading.Thread(
            target=worker,
            args=(q, stats, print_lock),
            daemon=True
        )
        t.start()
        threads.append(t)

    # ── Step 5: progress display loop ─────────────────────────────────────────
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(15)
            print(stats.summary())
    except KeyboardInterrupt:
        print("\n  Interrupted — waiting for in-flight requests to finish...")

    for t in threads:
        t.join()

    # ── Step 6: final summary ─────────────────────────────────────────────────
    print("\n" + stats.summary())
    total_done = sum(stats.done.values())
    total_err  = sum(stats.errors.values())
    print(f"\n{'═'*68}")
    print(f"  DONE  —  {total_done:,} saved   {total_err:,} errors")
    print(f"  Output: {OUT_DIR}")
    print(f"{'═'*68}\n")


if __name__ == "__main__":
    main()
