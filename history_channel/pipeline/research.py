"""Newspaper research: what the papers of the time actually printed.

    python run.py episodes/plague research          # uses `research:` in episode.yaml
    bash share_review.sh plague                      # pushes research/*.md with the review sheets

Writes episodes/<ep>/research/newspapers.md (readable list, newest-first per query) and newspapers.json.
Claude reads that file from the repo, picks headlines, quotes and page clippings, and writes them into the script.

Sources (keys go in history_channel/.env, never in chat or in git):
  chronam   Chronicling America, Library of Congress: US newspapers 1770-1963 (no key). Page scans 1770-1929
            are public domain in the US and can be shown on screen.
  nyt       New York Times Article Search API (NYT_API_KEY): headlines, abstracts, dates back to 1851.
            Use for research and for quoting headlines; the NYT scans themselves are not reused.
  trove     National Library of Australia (TROVE_KEY): Australian newspapers, worldwide wire stories.
  digitalnz Papers Past via DigitalNZ (DIGITALNZ_KEY): New Zealand newspapers (e.g. Samoa 1918).
  dpla      Digital Public Library of America (DPLA_KEY): aggregated US archives.
  europeana Europeana newspapers (EUROPEANA_KEY, demo key works with limits).

episode.yaml:
    research:
      - {q: "influenza parade", from: 1918-09-20, to: 1918-10-31, sources: [chronam, nyt]}
      - {q: "Talune influenza", from: 1918-11-01, to: 1919-01-31, sources: [digitalnz, trove]}
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .archives import SESSION, _strip_html

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _get(url, params=None, headers=None, tries=4):
    for a in range(tries):
        r = SESSION.get(url, params=params, headers=headers or {}, timeout=40)
        if r.status_code == 429:
            time.sleep(12 * (a + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("rate limited: " + url)


def _d(s):  # 1918-09-20 -> 19180920
    return str(s).replace("-", "")


# ---------------------------------------------------------------- sources
def nyt(q, d0, d1, n=30):
    key = os.environ.get("NYT_API_KEY")
    if not key:
        return None
    out = []
    for page in range(max(1, n // 10)):
        data = _get("https://api.nytimes.com/svc/search/v2/articlesearch.json",
                    {"q": q, "begin_date": _d(d0), "end_date": _d(d1), "sort": "oldest", "page": page, "api-key": key})
        docs = (data.get("response") or {}).get("docs") or []
        for x in docs:
            h = x.get("headline") or {}
            out.append({"source": "NYT", "date": (x.get("pub_date") or "")[:10],
                        "headline": h.get("main") or h.get("print_headline") or "",
                        "text": x.get("abstract") or x.get("snippet") or x.get("lead_paragraph") or "",
                        "page": x.get("print_page"), "url": x.get("web_url")})
        if len(docs) < 10:
            break
        time.sleep(13)   # NYT allows ~5 requests a minute
    return out


def chronam(q, d0, d1, n=40):
    data = _get("https://www.loc.gov/collections/chronicling-america/",
                {"q": q, "dates": f"{d0}/{d1}", "fo": "json", "c": str(n), "sb": "date"})
    out = []
    for r in data.get("results", []):
        img = (r.get("image_url") or [None])[-1]
        if img and img.startswith("//"):
            img = "https:" + img
        paper = r.get("partof_title") or r.get("title") or ""
        if isinstance(paper, list):
            paper = paper[0] if paper else ""
        loc = r.get("location_city") or r.get("location") or ""
        if isinstance(loc, list):
            loc = ", ".join(loc[:2])
        desc = r.get("description") or ""
        if isinstance(desc, list):
            desc = " ".join(desc)
        out.append({"source": "Chronicling America", "date": r.get("date", ""), "headline": paper,
                    "text": _strip_html(desc)[:400], "place": loc, "url": r.get("url") or r.get("id"),
                    "image": img, "public_domain": str(r.get("date", "0000"))[:4] < "1929"})
    return out


def trove(q, d0, d1, n=30):
    key = os.environ.get("TROVE_KEY")
    if not key:
        return None
    y0, y1 = int(str(d0)[:4]), int(str(d1)[:4])
    out = []
    for y in range(y0, y1 + 1):
        data = _get("https://api.trove.nla.gov.au/v3/result",
                    {"category": "newspaper", "q": q, "l-decade": str(y)[:3], "l-year": str(y), "n": str(n),
                     "encoding": "json", "sortby": "dateasc"}, headers={"X-API-KEY": key})
        for cat in data.get("category", []):
            for a in (cat.get("records") or {}).get("article", []):
                date = a.get("date", "")
                if not (str(d0) <= date <= str(d1)):
                    continue
                out.append({"source": "Trove", "date": date, "headline": _strip_html(a.get("heading", "")),
                            "text": _strip_html(a.get("snippet", ""))[:400],
                            "place": (a.get("title") or {}).get("title", ""), "url": a.get("troveUrl")})
    return out


def digitalnz(q, d0, d1, n=40):
    key = os.environ.get("DIGITALNZ_KEY")
    if not key:
        return None
    y0, y1 = int(str(d0)[:4]), int(str(d1)[:4])
    out = []
    for y in range(y0, y1 + 1):
        data = _get("https://api.digitalnz.org/records.json",
                    {"text": q, "and[category][]": "Newspapers", "and[year][]": str(y), "per_page": str(n)},
                    headers={"Authentication-Token": key})
        for r in (data.get("search") or {}).get("results", []):
            date = (r.get("date") or [""])[0][:10]
            if date and not (str(d0) <= date <= str(d1)):
                continue
            out.append({"source": "Papers Past", "date": date, "headline": r.get("title", ""),
                        "text": (r.get("description") or "")[:400],
                        "place": ", ".join(r.get("display_collection") and [r["display_collection"]] or []),
                        "url": r.get("landing_url")})
    return out


def dpla(q, d0, d1, n=30):
    key = os.environ.get("DPLA_KEY")
    if not key:
        return None
    data = _get("https://api.dp.la/v2/items", {"q": q, "api_key": key, "page_size": str(n),
                                               "sourceResource.date.after": str(d0), "sourceResource.date.before": str(d1)})
    out = []
    for d in data.get("docs", []):
        sr = d.get("sourceResource") or {}
        title = sr.get("title")
        title = title[0] if isinstance(title, list) and title else title or ""
        date = (sr.get("date") or {})
        date = date[0] if isinstance(date, list) and date else date
        out.append({"source": "DPLA", "date": (date or {}).get("displayDate", ""), "headline": title,
                    "text": " ".join(sr.get("description", []) if isinstance(sr.get("description"), list) else [sr.get("description") or ""])[:300],
                    "place": (d.get("dataProvider") or {}).get("name", "") if isinstance(d.get("dataProvider"), dict) else str(d.get("dataProvider", "")),
                    "url": d.get("isShownAt"), "image": d.get("object"), "rights": sr.get("rights") or d.get("rights")})
    return out


def europeana_news(q, d0, d1, n=30):
    key = os.environ.get("EUROPEANA_KEY", "api2demo")
    data = _get("https://api.europeana.eu/record/v2/search.json",
                {"wskey": key, "query": f"{q} AND YEAR:[{str(d0)[:4]} TO {str(d1)[:4]}]",
                 "theme": "newspaper", "rows": str(n), "profile": "standard"})
    out = []
    for it in data.get("items", []):
        out.append({"source": "Europeana", "date": " ".join(str(y) for y in it.get("year", [])),
                    "headline": (it.get("title") or [""])[0], "text": " ".join(it.get("dcDescription") or [])[:300],
                    "place": (it.get("dataProvider") or [""])[0], "url": (it.get("guid") or "").split("?")[0],
                    "image": (it.get("edmIsShownBy") or [None])[0], "rights": (it.get("rights") or [""])[0]})
    return out


SOURCES = {"chronam": chronam, "nyt": nyt, "trove": trove, "digitalnz": digitalnz, "dpla": dpla, "europeana": europeana_news}


def research(ep_dir: Path, episode: dict):
    load_env()
    jobs = episode.get("research") or []
    if not jobs:
        print("no `research:` block in episode.yaml")
        return
    out_dir = ep_dir / "research"
    out_dir.mkdir(exist_ok=True)
    allres, md = [], [f"# Newspapers: {episode['title']}", ""]
    for j in jobs:
        q, d0, d1 = j["q"], j["from"], j["to"]
        md += [f"## “{q}” · {d0} → {d1}", ""]
        for s in j.get("sources", ["chronam", "nyt"]):
            try:
                res = SOURCES[s](q, d0, d1)
            except Exception as e:
                md += [f"*{s}: error {str(e)[:120]}*", ""]
                print(f"   ! {s}: {e}")
                continue
            if res is None:
                md += [f"*{s}: no API key in .env, skipped*", ""]
                continue
            print(f"[{s}] {q}: {len(res)} results")
            for r in res:
                r["query"] = q
            allres += res
            for r in res:
                line = f"- **{r['date']}** · {r['source']}{' · ' + r['place'] if r.get('place') else ''} · {r['headline']}"
                if r.get("text"):
                    line += f" — {r['text'][:280]}"
                line += f" [link]({r['url']})" if r.get("url") else ""
                if r.get("image"):
                    line += f" [page image]({r['image']})"
                md.append(line)
            md.append("")
    (out_dir / "newspapers.md").write_text("\n".join(md))
    (out_dir / "newspapers.json").write_text(json.dumps(allres, indent=1, ensure_ascii=False))
    print(f"research: {len(allres)} items -> {out_dir / 'newspapers.md'}")
