"""Search public archives and keep only images that are safe to use on a monetized channel.

Sources:
  commons   - Wikimedia Commons (huge, mirrors LoC/NARA/CDC/Wellcome items, good license metadata)
  loc       - Library of Congress (photos & prints)
  wellcome  - Wellcome Collection (history of medicine)

Every candidate carries: source, id, title, page_url, download_url, license, credit, width, height.
Only licenses in ALLOWED are returned. NC (non-commercial) and ND (no-derivatives) are always rejected,
because a monetized YouTube video is commercial use and Ken Burns motion/cropping is a derivative.
"""
from __future__ import annotations

import html
import re
import time

import requests

UA = "ArchiveHistoryPipeline/0.1 (educational YouTube channel; contact: set CONTACT_EMAIL)"
SESSION = requests.Session()
SESSION.headers["User-Agent"] = UA
MIN_WIDTH = 900


def _get(url, params=None, retries=3, timeout=30):
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=timeout)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def _strip_html(s: str | None) -> str:
    if not s:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


# ---------------------------------------------------------------- license rules
# ShareAlike (CC BY-SA) arguably forces the whole video to be released under BY-SA.
# Off by default for a monetized channel; flip to True if you accept that.
ALLOW_SHARE_ALIKE = False


def license_ok(lic: str) -> bool:
    l = lic.lower().replace("_", "-")
    tokens = re.split(r"[-\s/,.]", l)
    if "nc" in tokens or "nd" in tokens:
        return False
    if "sa" in tokens and not ALLOW_SHARE_ALIKE:
        return False
    if "non-commercial" in l or "noncommercial" in l or "no derivatives" in l:
        return False
    good = ("public domain", "pd", "pdm", "cc0", "cc-0", "cc by", "cc-by", "no known restrictions",
            "no known copyright", "us government", "pd-usgov")
    return any(l.startswith(g) or g in l for g in good)


# ---------------------------------------------------------------- Wikimedia Commons
def search_commons(query: str, limit: int = 20) -> list[dict]:
    params = {
        "action": "query", "format": "json", "formatversion": "2",
        "generator": "search", "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": "3000",
    }
    data = _get("https://commons.wikimedia.org/w/api.php", params).json()
    pages = sorted(data.get("query", {}).get("pages", []), key=lambda p: p.get("index", 999))
    out = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png", "image/tiff"):
            continue
        md = ii.get("extmetadata", {})
        lic = _strip_html(md.get("LicenseShortName", {}).get("value")) or _strip_html(md.get("License", {}).get("value"))
        if not lic or not license_ok(lic):
            continue
        if ii.get("width", 0) < MIN_WIDTH:
            continue
        artist = _strip_html(md.get("Artist", {}).get("value"))
        credit = _strip_html(md.get("Credit", {}).get("value"))
        date = _strip_html(md.get("DateTimeOriginal", {}).get("value"))
        title = p["title"].removeprefix("File:").rsplit(".", 1)[0]
        out.append({
            "source": "commons",
            "id": f"commons:{p['pageid']}",
            "title": title,
            "description": _strip_html(md.get("ImageDescription", {}).get("value"))[:400],
            "date": date,
            "page_url": ii.get("descriptionurl"),
            # thumburl is a server-side resize to <=3000px wide, avoids 100MB TIFF originals
            "download_url": ii.get("thumburl") or ii.get("url"),
            "license": lic,
            "credit": ", ".join(x for x in (artist, credit) if x)[:200] or "Wikimedia Commons",
            "width": ii.get("width"), "height": ii.get("height"),
        })
    return out


# ---------------------------------------------------------------- Library of Congress
def _loc_rights(item: dict) -> str:
    texts = []
    for k in ("rights_advisory", "rights", "rights_information"):
        v = item.get(k)
        if isinstance(v, list):
            texts += [str(x) for x in v]
        elif v:
            texts.append(str(v))
    return " ".join(texts)


def _loc_best_image(data: dict) -> tuple[str | None, int, int]:
    best = (None, 0, 0)
    for res in data.get("resources", []) or []:
        files = res.get("files") or []
        for group in files:
            for f in (group if isinstance(group, list) else [group]):
                if f.get("mimetype") == "image/jpeg" and f.get("width"):
                    if f["width"] > best[1] and f["width"] <= 4000:
                        best = (f.get("url"), f["width"], f.get("height") or 0)
        if best[0]:
            break
    if not best[0]:
        urls = data.get("item", {}).get("image_url") or data.get("image_url") or []
        if urls:
            u = urls[-1].split("#")[0]
            best = (("https:" + u) if u.startswith("//") else u, 0, 0)
    return best


def search_loc(query: str, limit: int = 15) -> list[dict]:
    data = _get("https://www.loc.gov/photos/", {"q": query, "fo": "json", "c": str(limit)}).json()
    out = []
    for r in data.get("results", []):
        item_url = r.get("url") or r.get("id")
        if not item_url or not r.get("image_url"):
            continue
        if r.get("access_restricted"):
            continue
        time.sleep(0.7)  # LoC asks for gentle crawling
        try:
            d = _get(item_url.rstrip("/") + "/", {"fo": "json"}).json()
        except Exception:
            continue
        item = d.get("item", {})
        rights = _loc_rights(item)
        if not rights or not license_ok(rights):
            continue
        url, w, h = _loc_best_image(d)
        if not url or (w and w < MIN_WIDTH):
            continue
        call = item.get("call_number") or item.get("reproduction_number") or ""
        if isinstance(call, list):
            call = call[0] if call else ""
        out.append({
            "source": "loc",
            "id": "loc:" + item_url.rstrip("/").rsplit("/", 1)[-1],
            "title": r.get("title", "")[:200],
            "description": " ".join(item.get("summary") or [])[:400] if isinstance(item.get("summary"), list) else "",
            "date": r.get("date", ""),
            "page_url": item_url,
            "download_url": url,
            "license": "No known restrictions on publication (Library of Congress)",
            "credit": f"Library of Congress{', ' + call if call else ''}",
            "width": w, "height": h,
        })
    return out


# ---------------------------------------------------------------- Wellcome Collection
def search_wellcome(query: str, limit: int = 20) -> list[dict]:
    data = _get("https://api.wellcomecollection.org/catalogue/v2/images",
                {"query": query, "pageSize": str(limit)}).json()
    out = []
    for r in data.get("results", []):
        loc = (r.get("locations") or [{}])[0]
        lic = loc.get("license") or {}
        lic_id = lic.get("id", "")
        if lic_id not in ("pdm", "cc-0", "cc-by"):
            continue
        info = loc.get("url", "")
        if not info.endswith("info.json"):
            continue
        src = r.get("source") or {}
        out.append({
            "source": "wellcome",
            "id": f"wellcome:{r['id']}",
            "title": src.get("title", "")[:200],
            "description": "",
            "date": "",
            "page_url": f"https://wellcomecollection.org/works/{src.get('id')}" if src.get("id") else "https://wellcomecollection.org",
            "download_url": info.replace("info.json", "full/max/0/default.jpg"),
            "download_fallbacks": [info.replace("info.json", s) for s in
                                   ("full/full/0/default.jpg", "full/2048,/0/default.jpg", "full/1338,/0/default.jpg")],
            "license": lic.get("label") or lic_id,
            "credit": "Wellcome Collection" + (" (CC BY 4.0)" if lic_id == "cc-by" else ""),
            "width": 0, "height": 0,
        })
    return out


SOURCES = {"commons": search_commons, "loc": search_loc, "wellcome": search_wellcome}


DISABLED: set[str] = set()


def search_all(query: str, sources=("commons", "wellcome", "loc")) -> list[dict]:
    """Interleave results so one archive does not dominate the scene.

    Commons goes first: it has the best license metadata and mirrors most LoC/NARA/CDC photos.
    loc.gov sometimes answers scripts with a Cloudflare bot check; then it is skipped for the run.
    """
    lists = []
    for s in sources:
        if s in DISABLED:
            continue
        try:
            lists.append(SOURCES[s](query))
        except Exception as e:  # one archive being down must not stop the episode
            print(f"   ! {s} unavailable ({str(e)[:80]}), skipping it for this run")
            DISABLED.add(s)
            lists.append([])
    out = []
    for i in range(max((len(l) for l in lists), default=0)):
        for l in lists:
            if i < len(l):
                out.append(l[i])
    return out
