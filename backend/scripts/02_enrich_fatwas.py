"""
02_enrich_fatwas.py
Parses Quran citations from fatwa text (e.g. [البقرة:173]) and attaches
verified Arabic verse text from quran_verses.json.
Outputs enriched_fatwas.jsonl with an extra `quran_citations` field.
"""
import json
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
FATWA_PATH = DATA_DIR / "fatwa.jsonl"
QURAN_PATH = DATA_DIR / "quran_verses.json"
OUTPUT_PATH = DATA_DIR / "enriched_fatwas.jsonl"

# Regex patterns for Quran citations in fatwa text
# Matches: [البقرة:173] or [الأنعام:19] or (النساء: 142-143)
CITATION_PATTERNS = [
    # [سورة:آية] or [سورة: آية]
    re.compile(r'[\[﴿]\s*([^\]:﴾]+?)\s*:\s*(\d+(?:\s*[-–,،]\s*\d+)?)\s*[\]﴾]'),
    # سورة الأنعام: آية 19 or similar
    re.compile(r'سورة\s+([^\s:]+)\s*:\s*(\d+(?:\s*[-–,،]\s*\d+)?)'),
    # {البقرة:173}
    re.compile(r'\{\s*([^\}:]+?)\s*:\s*(\d+(?:\s*[-–,،]\s*\d+)?)\s*\}'),
]


def load_quran() -> dict:
    """Load pre-downloaded Quran verses."""
    if not QURAN_PATH.exists():
        print(f"❌ {QURAN_PATH} not found. Run 01_download_quran.py first.")
        sys.exit(1)

    data = json.loads(QURAN_PATH.read_text(encoding="utf-8"))
    return data


def parse_ayah_range(ayah_str: str) -> list[int]:
    """Parse '173' → [173] or '142-143' → [142, 143] or '1,2,3' → [1,2,3]."""
    ayah_str = ayah_str.strip()

    # Range: 142-143
    if '-' in ayah_str or '–' in ayah_str:
        parts = re.split(r'[-–]', ayah_str)
        try:
            start, end = int(parts[0].strip()), int(parts[-1].strip())
            return list(range(start, end + 1))
        except ValueError:
            return []

    # Comma-separated: 1,2,3
    if ',' in ayah_str or '،' in ayah_str:
        parts = re.split(r'[,،]', ayah_str)
        try:
            return [int(p.strip()) for p in parts if p.strip().isdigit()]
        except ValueError:
            return []

    # Single number
    try:
        return [int(ayah_str)]
    except ValueError:
        return []


def extract_citations(text: str, quran_data: dict) -> list[dict]:
    """Extract all Quran citations from fatwa text and verify against Quran data."""
    name_to_num = quran_data["surah_name_to_number"]
    verses = quran_data["verses"]
    citations = []
    seen = set()

    for pattern in CITATION_PATTERNS:
        for match in pattern.finditer(text):
            surah_name = match.group(1).strip()
            ayah_str = match.group(2).strip()

            # Remove common prefixes
            clean_name = surah_name.replace("سورة", "").strip()

            # Lookup surah number
            surah_num = name_to_num.get(clean_name)
            if not surah_num:
                # Try fuzzy: check if name is a substring of any surah name
                for known_name, num in name_to_num.items():
                    if clean_name in known_name or known_name in clean_name:
                        surah_num = num
                        break

            if not surah_num:
                continue

            ayah_numbers = parse_ayah_range(ayah_str)
            for ayah_num in ayah_numbers:
                key = f"{surah_num}:{ayah_num}"
                if key in seen:
                    continue
                seen.add(key)

                # Get verified text
                surah_verses = verses.get(str(surah_num), {})
                verified_text = surah_verses.get(str(ayah_num), "")

                surah_name_clean = quran_data["surah_names"].get(str(surah_num), clean_name)

                citations.append({
                    "reference": f"{surah_name_clean}:{ayah_num}",
                    "surah_number": surah_num,
                    "ayah_number": ayah_num,
                    "surah_name": surah_name_clean,
                    "verified_text": verified_text,
                    "quran_url": f"https://quran.com/{surah_num}/{ayah_num}",
                })

    return citations


def main():
    print("📖 Loading Quran verses...")
    quran_data = load_quran()
    total_verses = sum(len(v) for v in quran_data["verses"].values())
    print(f"   ✅ Loaded {total_verses} verses from {len(quran_data['verses'])} surahs.")

    print(f"\n📝 Processing fatwas from {FATWA_PATH.name}...")
    total = 0
    with_citations = 0
    total_citations = 0

    with open(FATWA_PATH, "r", encoding="utf-8") as fin, \
         open(OUTPUT_PATH, "w", encoding="utf-8") as fout:

        for line in fin:
            if not line.strip():
                continue
            fatwa = json.loads(line)
            total += 1

            # Parse citations from answer text
            full_text = f"{fatwa.get('answer', '')} {fatwa.get('question', '')}"
            citations = extract_citations(full_text, quran_data)

            fatwa["quran_citations"] = citations
            if citations:
                with_citations += 1
                total_citations += len(citations)

            fout.write(json.dumps(fatwa, ensure_ascii=False) + "\n")

            if total % 5000 == 0:
                print(f"   Processed {total:,} fatwas...")

    print(f"\n✅ Done!")
    print(f"   Total fatwas: {total:,}")
    print(f"   With Quran citations: {with_citations:,} ({with_citations/total*100:.1f}%)")
    print(f"   Total citations found: {total_citations:,}")
    print(f"   Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
