"""
04_load_content.py
Loads articles, books, speeches, discussions, and audios into SQLite (content.db).
"""
import json
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings

DATA_DIR       = Path(settings.data_dir)
DB_PATH        = settings.content_db_path
SCRAPER_OUTPUT = Path(__file__).parent.parent.parent / "scraper" / "output"


def create_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE, title TEXT, text TEXT,
            source_ref TEXT, categories TEXT, date TEXT, scraped_at TEXT
        );
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE, title TEXT, pdf_url TEXT, scraped_at TEXT
        );
        CREATE TABLE IF NOT EXISTS speeches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE, title TEXT, text TEXT,
            source_ref TEXT, categories TEXT, date TEXT, scraped_at TEXT
        );
        CREATE TABLE IF NOT EXISTS discussions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE, title TEXT, text TEXT,
            source_ref TEXT, categories TEXT, date TEXT, scraped_at TEXT
        );
        CREATE TABLE IF NOT EXISTS audios (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            url        TEXT UNIQUE,
            title      TEXT,
            transcript TEXT,
            audio_url  TEXT,
            categories TEXT,
            scraped_at TEXT
        );
        DROP VIEW IF EXISTS content_stats;
        CREATE VIEW content_stats AS
            SELECT 'articles'    as type, COUNT(*) as count FROM articles
            UNION ALL SELECT 'books',       COUNT(*) FROM books
            UNION ALL SELECT 'speeches',    COUNT(*) FROM speeches
            UNION ALL SELECT 'discussions', COUNT(*) FROM discussions
            UNION ALL SELECT 'audios',      COUNT(*) FROM audios;
    """)
    print("✅ Tables created.")


def load_jsonl(file_path: Path) -> list[dict]:
    """Check DATA_DIR first, then SCRAPER_OUTPUT (auto-copies on first find)."""
    for path in [file_path, SCRAPER_OUTPUT / file_path.name]:
        if path.exists():
            items = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        items.append(json.loads(line))
            if path != file_path:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, file_path)
                print(f"  📋 Copied {path.name} → {file_path}")
            return items
    print(f"  ⚠️  {file_path.name} not found, skipping.")
    return []


def insert_articles(conn, items):
    for a in items:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO articles (url,title,text,source_ref,categories,date,scraped_at) VALUES (?,?,?,?,?,?,?)",
                (a.get("url",""), a.get("title",""), a.get("text",""), a.get("source_ref",""),
                 json.dumps(a.get("categories",[]), ensure_ascii=False), a.get("date",""), a.get("scraped_at",""))
            )
        except Exception as e:
            print(f"  ⚠️  {e}")


def insert_books(conn, items):
    for b in items:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO books (url,title,pdf_url,scraped_at) VALUES (?,?,?,?)",
                (b.get("url",""), b.get("title",""), b.get("pdf_url",""), b.get("scraped_at",""))
            )
        except Exception as e:
            print(f"  ⚠️  {e}")


def insert_speeches(conn, items):
    for s in items:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO speeches (url,title,text,source_ref,categories,date,scraped_at) VALUES (?,?,?,?,?,?,?)",
                (s.get("url",""), s.get("title",""), s.get("text",""), s.get("source_ref",""),
                 json.dumps(s.get("categories",[]), ensure_ascii=False), s.get("date",""), s.get("scraped_at",""))
            )
        except Exception as e:
            print(f"  ⚠️  {e}")


def insert_discussions(conn, items):
    for d in items:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO discussions (url,title,text,source_ref,categories,date,scraped_at) VALUES (?,?,?,?,?,?,?)",
                (d.get("url",""), d.get("title",""), d.get("text",""), d.get("source_ref",""),
                 json.dumps(d.get("categories",[]), ensure_ascii=False), d.get("date",""), d.get("scraped_at",""))
            )
        except Exception as e:
            print(f"  ⚠️  {e}")


def insert_audios(conn, items):
    for a in items:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO audios (url,title,transcript,audio_url,categories,qa_pairs,scraped_at) VALUES (?,?,?,?,?,?,?)",
                (a.get("url",""), a.get("title",""),
                 a.get("transcript", a.get("text","")),
                 a.get("audio_url",""),
                 json.dumps(a.get("categories",[]), ensure_ascii=False),
                 json.dumps(a.get("qa_pairs",[]), ensure_ascii=False),
                 a.get("scraped_at",""))
            )
        except Exception as e:
            print(f"  ⚠️  {e}")


LOADERS = [
    ("article.jsonl",    insert_articles),
    ("book.jsonl",       insert_books),
    ("speech.jsonl",     insert_speeches),
    ("discussion.jsonl", insert_discussions),
    ("audio.jsonl",      insert_audios),
]


def main():
    print(f"📦 Loading content into SQLite: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)

    for filename, load_fn in LOADERS:
        items = load_jsonl(DATA_DIR / filename)
        if items:
            load_fn(conn, items)
            conn.commit()
            print(f"  ✅ {len(items):,} {filename.replace('.jsonl','')}")

    print("\n📊 Content DB Stats:")
    for row in conn.execute("SELECT * FROM content_stats"):
        print(f"   {row[0]}: {row[1]:,}")

    conn.close()
    print(f"\n💾 Database saved to: {DB_PATH}")


if __name__ == "__main__":
    main()
