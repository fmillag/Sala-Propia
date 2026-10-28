"""Lee el feed RSS de Letterboxd y actualiza sync-data.js.

- extra_watched: películas vistas que no estaban en el export original (base-keys.json).
- diary: cada entrada del diario que trae el feed (incluye revisionados), sin duplicar.
- last_sync: fecha de la última sincronización.

El feed solo trae las ~50 entradas más recientes, por eso corre todos los días y acumula.
Uso: python sync_letterboxd.py [usuario]
"""
import datetime
import json
import sys
import unicodedata
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

USER = sys.argv[1] if len(sys.argv) > 1 else "fmillag"
HERE = Path(__file__).parent
DATA = HERE / "sync-data.js"
PREFIX = "window.SYNC = "
NS = {"lb": "https://letterboxd.com", "tmdb": "https://themoviedb.org"}


def film_key(title, year):
    # mismo resultado que filmKey() en index.html
    t = unicodedata.normalize("NFD", title.lower())
    t = "".join(c for c in t if not 0x300 <= ord(c) <= 0x36F)
    return re.sub(r"[^a-z0-9]+", " ", t).strip() + "|" + str(year)


def load():
    raw = DATA.read_text(encoding="utf-8").strip()
    return json.loads(raw[len(PREFIX):].rstrip(";"))


def save(data):
    DATA.write_text(PREFIX + json.dumps(data, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")


def fetch_feed():
    req = urllib.request.Request(
        f"https://letterboxd.com/{USER}/rss/",
        headers={"User-Agent": "Mozilla/5.0 (sala-propia sync)"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return ET.fromstring(r.read())


def entries(root):
    for item in root.iter("item"):
        date = item.findtext("lb:watchedDate", namespaces=NS)
        title = item.findtext("lb:filmTitle", namespaces=NS)
        if not date or not title:  # listas y otras entradas que no son del diario
            continue
        year = int(item.findtext("lb:filmYear", "0", NS) or 0)
        rating = item.findtext("lb:memberRating", namespaces=NS)
        tmdb = item.findtext("tmdb:movieId", namespaces=NS)
        yield {
            "title": title,
            "year": year,
            "rating": float(rating) if rating else None,
            "date": date,
            "rewatch": 1 if item.findtext("lb:rewatch", namespaces=NS) == "Yes" else 0,
            "tmdb": int(tmdb) if tmdb else 0,
        }


def main():
    data = load()
    base = set(json.loads((HERE / "base-keys.json").read_text(encoding="utf-8")))
    extra_keys = {film_key(r[0], r[1]) for r in data["extra_watched"]}
    diary_keys = {film_key(r[0], r[1]) + "@" + r[3] for r in data["diary"]}

    added_extra = added_diary = 0
    for e in sorted(entries(fetch_feed()), key=lambda e: e["date"]):
        k = film_key(e["title"], e["year"])
        if k not in base and k not in extra_keys:
            data["extra_watched"].append([e["title"], e["year"], e["rating"], e["date"], e["tmdb"]])
            extra_keys.add(k)
            added_extra += 1
        if k + "@" + e["date"] not in diary_keys:
            data["diary"].append([e["title"], e["year"], e["rating"], e["date"], e["rewatch"], e["tmdb"]])
            diary_keys.add(k + "@" + e["date"])
            added_diary += 1

    data["diary"].sort(key=lambda r: r[3])
    data["last_sync"] = datetime.date.today().isoformat()
    save(data)
    print(f"{added_extra} películas nuevas, {added_diary} entradas de diario nuevas")


if __name__ == "__main__":
    main()
