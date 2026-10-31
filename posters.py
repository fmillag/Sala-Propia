"""Busca en Wikipedia el cartel de cada película recomendable (CATALOG_ALL y TERROR_LIST de index.html)
y lo guarda en posters.js. Solo consulta las que todavía no están, así que las corridas diarias son casi instantáneas.

Uso: python posters.py [--retry]   (--retry vuelve a intentar las que no se encontraron)
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from sync_letterboxd import film_key

HERE = Path(__file__).parent
OUT = HERE / "posters.js"
PREFIX = "window.POSTERS = "
API = "https://en.wikipedia.org/w/api.php"
UA = "SalaPropia/1.0 (https://github.com/fmillag/Sala-Propia)"


def films():
    for line in (HERE / "index.html").read_text(encoding="utf-8").splitlines():
        for name in ("CATALOG_ALL", "TERROR_LIST"):
            pfx = f"const {name} = "
            if line.startswith(pfx):
                for row in json.loads(line[len(pfx):].rstrip().rstrip(";")):
                    yield row[0], row[1]


def api(**params):
    params.update(format="json", formatversion=2)
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pages(titles):
    q = api(action="query", titles="|".join(titles), redirects=1, prop="pageimages|description",
            piprop="thumbnail", pithumbsize=342, pilicense="any")["query"]
    found = {p["title"]: p for p in q.get("pages", []) if not p.get("missing")}
    # deshace redirecciones/normalizaciones para respetar el orden de preferencia
    alias = {}
    for kind in ("normalized", "redirects"):
        for m in q.get(kind, []):
            alias[m["from"]] = alias.get(m["to"], m["to"])
    for t in titles:
        t2 = alias.get(t, t)
        t2 = alias.get(t2, t2)
        if t2 in found:
            yield found[t2]


def is_match(page, year):
    if "thumbnail" not in page:
        return False
    if page["title"].endswith(f"({year} film)"):  # el título ya dice año y que es película
        return True
    desc = (page.get("description") or "").lower()
    return ("film" in desc or "movie" in desc) and any(str(y) in desc for y in (year - 1, year, year + 1))


def lookup(title, year):
    for p in pages([f"{title} ({year} film)", f"{title} (film)", title]):
        if is_match(p, year):
            return p["thumbnail"]["source"]
    hits = api(action="query", list="search", srsearch=f"{title} {year} film", srlimit=3)["query"]["search"]
    for p in pages([h["title"] for h in hits]):
        if is_match(p, year):
            return p["thumbnail"]["source"]
    return None


def main():
    retry = "--retry" in sys.argv
    posters = json.loads(OUT.read_text(encoding="utf-8")[len(PREFIX):].strip().rstrip(";")) if OUT.exists() else {}
    todo = [(t, y) for t, y in dict.fromkeys(films())
            if film_key(t, y) not in posters or (retry and posters[film_key(t, y)] is None)]
    for t, y in todo:
        try:
            posters[film_key(t, y)] = lookup(t, y)
        except Exception as e:  # un error de red no frena el resto; se reintenta mañana
            print("error", t, y, e)
            continue
        time.sleep(0.2)
    OUT.write_text(PREFIX + json.dumps(posters, ensure_ascii=False, indent=0, sort_keys=True) + ";\n", encoding="utf-8")
    missing = sorted(k for k, v in posters.items() if v is None)
    print(f"{len(todo)} consultadas; {len(posters) - len(missing)} con cartel, {len(missing)} sin cartel")
    for k in missing:
        print("  sin cartel:", k)


if __name__ == "__main__":
    main()
