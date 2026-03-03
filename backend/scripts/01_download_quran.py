"""
01_download_quran.py
Fetches all 6,236 Quran verses from AlQuran Cloud API (Arabic text).
Saves to data/quran_verses.json as {surah_number: {ayah_number: text}}.
Run once.
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx

API_BASE = "https://api.alquran.cloud/v1"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "quran_verses.json"

# Surah names (Arabic) for reference
SURAH_NAMES = {
    1: "الفاتحة", 2: "البقرة", 3: "آل عمران", 4: "النساء", 5: "المائدة",
    6: "الأنعام", 7: "الأعراف", 8: "الأنفال", 9: "التوبة", 10: "يونس",
    11: "هود", 12: "يوسف", 13: "الرعد", 14: "إبراهيم", 15: "الحجر",
    16: "النحل", 17: "الإسراء", 18: "الكهف", 19: "مريم", 20: "طه",
    21: "الأنبياء", 22: "الحج", 23: "المؤمنون", 24: "النور", 25: "الفرقان",
    26: "الشعراء", 27: "النمل", 28: "القصص", 29: "العنكبوت", 30: "الروم",
    31: "لقمان", 32: "السجدة", 33: "الأحزاب", 34: "سبأ", 35: "فاطر",
    36: "يس", 37: "الصافات", 38: "ص", 39: "الزمر", 40: "غافر",
    41: "فصلت", 42: "الشورى", 43: "الزخرف", 44: "الدخان", 45: "الجاثية",
    46: "الأحقاف", 47: "محمد", 48: "الفتح", 49: "الحجرات", 50: "ق",
    51: "الذاريات", 52: "الطور", 53: "النجم", 54: "القمر", 55: "الرحمن",
    56: "الواقعة", 57: "الحديد", 58: "المجادلة", 59: "الحشر", 60: "الممتحنة",
    61: "الصف", 62: "الجمعة", 63: "المنافقون", 64: "التغابن", 65: "الطلاق",
    66: "التحريم", 67: "الملك", 68: "القلم", 69: "الحاقة", 70: "المعارج",
    71: "نوح", 72: "الجن", 73: "المزمل", 74: "المدثر", 75: "القيامة",
    76: "الإنسان", 77: "المرسلات", 78: "النبأ", 79: "النازعات", 80: "عبس",
    81: "التكوير", 82: "الانفطار", 83: "المطففين", 84: "الانشقاق", 85: "البروج",
    86: "الطارق", 87: "الأعلى", 88: "الغاشية", 89: "الفجر", 90: "البلد",
    91: "الشمس", 92: "الليل", 93: "الضحى", 94: "الشرح", 95: "التين",
    96: "العلق", 97: "القدر", 98: "البينة", 99: "الزلزلة", 100: "العاديات",
    101: "القارعة", 102: "التكاثر", 103: "العصر", 104: "الهمزة", 105: "الفيل",
    106: "قريش", 107: "الماعون", 108: "الكوثر", 109: "الكافرون", 110: "النصر",
    111: "المسد", 112: "الإخلاص", 113: "الفلق", 114: "الناس",
}

# Reverse lookup: Arabic name → surah number
SURAH_NAME_TO_NUMBER = {name: num for num, name in SURAH_NAMES.items()}


async def fetch_full_quran(client: httpx.AsyncClient) -> dict:
    """Fetch entire Quran in one API call."""
    print("📖 Fetching full Quran from AlQuran Cloud API...")
    resp = await client.get(f"{API_BASE}/quran/ar.asad")

    if resp.status_code != 200:
        # Fallback: fetch surah by surah
        print("⚠️  Full Quran endpoint failed, falling back to per-surah fetch...")
        return await fetch_surah_by_surah(client)

    data = resp.json()
    if data.get("code") != 200:
        return await fetch_surah_by_surah(client)

    quran = {}
    for surah_data in data["data"]["surahs"]:
        surah_num = surah_data["number"]
        quran[str(surah_num)] = {}
        for ayah in surah_data["ayahs"]:
            ayah_in_surah = ayah["numberInSurah"]
            quran[str(surah_num)][str(ayah_in_surah)] = ayah["text"]

    return quran


async def fetch_surah_by_surah(client: httpx.AsyncClient) -> dict:
    """Fallback: fetch each surah individually."""
    quran = {}
    for surah_num in range(1, 115):
        surah_name = SURAH_NAMES.get(surah_num, f"Surah {surah_num}")
        print(f"  📖 Fetching surah {surah_num}/114: {surah_name}...")

        resp = await client.get(f"{API_BASE}/surah/{surah_num}/ar.asad")
        if resp.status_code != 200:
            print(f"  ❌ Failed to fetch surah {surah_num}, retrying...")
            await asyncio.sleep(2)
            resp = await client.get(f"{API_BASE}/surah/{surah_num}/ar.asad")

        data = resp.json()
        if data.get("code") == 200:
            quran[str(surah_num)] = {}
            for ayah in data["data"]["ayahs"]:
                ayah_in_surah = ayah["numberInSurah"]
                quran[str(surah_num)][str(ayah_in_surah)] = ayah["text"]

        # Rate limit courtesy
        await asyncio.sleep(0.3)

    return quran


async def main():
    if OUTPUT_PATH.exists():
        print(f"✅ {OUTPUT_PATH.name} already exists. Delete to re-download.")
        existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        total = sum(len(v) for v in existing.values())
        print(f"   Contains {len(existing)} surahs, {total} verses.")
        return

    async with httpx.AsyncClient(timeout=60) as client:
        quran = await fetch_full_quran(client)

    total_verses = sum(len(v) for v in quran.values())
    print(f"\n✅ Downloaded {len(quran)} surahs, {total_verses} verses.")

    # Add surah name lookup metadata
    output = {
        "surah_names": SURAH_NAMES,
        "surah_name_to_number": SURAH_NAME_TO_NUMBER,
        "verses": quran,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"💾 Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
