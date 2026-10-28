"""Search public archives and keep only images that are safe to use on a monetized channel.

Sources:
  commons     - Wikimedia Commons (huge, mirrors LoC/NARA/CDC/Wellcome items, good license metadata)
  smithsonian - Smithsonian Open Access (CC0 only). Key: SI_API_KEY (free at api.data.gov; DEMO_KEY is rate-limited)
  europeana   - Europeana, aggregated European archives. Key: EUROPEANA_KEY (free; "api2demo" for testing)
  wellcome    - Wellcome Collection (history of medicine)
  loc         - Library of Congress (photos & prints); sometimes answers scripts with a Cloudflare check

Every candidate carries: source, id, title, page_url, download_url, license, credit, width, height.
Only licenses in ALLOWED are returned. NC (non-commercial) and ND (no-derivatives) are always rejected,
because a monetized YouTube video is commercial use and Ken Burns motion/cropping is a derivative.
"""
from __future__ import annotations

import html
import os
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
def search_commons(query: str, limit: int = 30) -> list[dict]:
    params = {
        "action": "query", "format": "json", "formatversion": "2",
        "generator": "search", "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": "6",
        "gsrlimit": str(limit),  # noqa
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": "3000",
    }
    data = {}
    for attempt in range(5):   # Commons answers 200 + {"error": "cirrussearch-too-busy-error"} under load
        data = _get("https://commons.wikimedia.org/w/api.php", params).json()
        if "error" not in data:
            break
        time.sleep(2 + 3 * attempt)
    else:
        raise RuntimeError(f"Commons search failed: {data.get('error', {}).get('code')}")
    time.sleep(0.5)            # be polite: one search at a time
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


def commons_file(title: str) -> dict | None:
    """One specific Commons file, picked by hand (e.g. "File:Foo.jpg"). Licence is still checked."""
    params = {"action": "query", "format": "json", "formatversion": "2",
              "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": "3000"}
    if title.startswith("curid:"):            # page id, e.g. "curid:25513204" (short and unambiguous)
        params["pageids"] = title.split(":", 1)[1]
    else:
        title = title if title.startswith("File:") else "File:" + title
        params["titles"] = title
    data = {}
    for attempt in range(5):
        data = _get("https://commons.wikimedia.org/w/api.php", params).json()
        if "error" not in data:
            break
        time.sleep(2 + 3 * attempt)
    pages = data.get("query", {}).get("pages", [])
    if not pages or "imageinfo" not in pages[0]:
        print(f"   ! not found on Commons: {title}")
        return None
    p = pages[0]
    ii = p["imageinfo"][0]
    md = ii.get("extmetadata", {})
    lic = _strip_html(md.get("LicenseShortName", {}).get("value")) or _strip_html(md.get("License", {}).get("value"))
    if not lic or not license_ok(lic):
        print(f"   ! licence not allowed ({lic}): {title}")
        return None
    artist = _strip_html(md.get("Artist", {}).get("value"))
    credit = _strip_html(md.get("Credit", {}).get("value"))
    return {
        "source": "commons", "id": f"commons:{p['pageid']}",
        "title": p["title"].removeprefix("File:").rsplit(".", 1)[0],
        "description": _strip_html(md.get("ImageDescription", {}).get("value"))[:400],
        "date": _strip_html(md.get("DateTimeOriginal", {}).get("value")),
        "page_url": ii.get("descriptionurl"), "download_url": ii.get("thumburl") or ii.get("url"),
        "license": lic, "credit": ", ".join(x for x in (artist, credit) if x)[:200] or "Wikimedia Commons",
        "width": ii.get("width"), "height": ii.get("height"),
    }


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


# ---------------------------------------------------------------- Smithsonian Open Access (CC0)
def search_smithsonian(query: str, limit: int = 20) -> list[dict]:
    key = os.environ.get("SI_API_KEY", "DEMO_KEY")
    data = _get("https://api.si.edu/openaccess/api/v1.0/search",
                {"q": f"{query} AND online_media_type:Images", "rows": str(limit), "api_key": key}).json()
    out = []
    for row in data.get("response", {}).get("rows", []):
        dn = row.get("content", {}).get("descriptiveNonRepeating", {})
        for m in (dn.get("online_media") or {}).get("media", [])[:1]:
            if m.get("type") != "Images" or (m.get("usage") or {}).get("access") != "CC0":
                continue
            content = m.get("content") or ""
            if "deliveryService" not in content:
                continue
            dates = (row.get("content", {}).get("indexedStructured", {}) or {}).get("date") or []
            out.append({
                "source": "smithsonian",
                "id": f"smithsonian:{m.get('idsId') or content.split('id=')[-1]}",
                "title": (row.get("title") or "")[:200],
                "description": "",
                "date": " ".join(dates) if isinstance(dates, list) else str(dates),
                "page_url": dn.get("record_link") or dn.get("guid") or "https://www.si.edu/openaccess",
                "download_url": content + "&max=3000",
                "license": "CC0",
                "credit": f"Smithsonian ({row.get('unitCode', '')})",
                "width": 0, "height": 0,
            })
    return out


# ---------------------------------------------------------------- Europeana
EUROPEANA_OK = ("publicdomain/mark", "publicdomain/zero", "licenses/by/")


def search_europeana(query: str, limit: int = 20) -> list[dict]:
    key = os.environ.get("EUROPEANA_KEY", "api2demo")
    data = _get("https://api.europeana.eu/record/v2/search.json",
                {"wskey": key, "query": query, "qf": "TYPE:IMAGE", "reusability": "open",
                 "media": "true", "rows": str(limit), "profile": "standard"}).json()
    out = []
    for it in data.get("items", []):
        rights = (it.get("rights") or [""])[0]
        if not any(r in rights for r in EUROPEANA_OK):
            continue
        by = (it.get("edmIsShownBy") or [None])[0]
        if not by:
            continue
        # IIIF previews are often sized down ("/full/512,/"); ask for a large version instead
        by = re.sub(r"/full/\d*,\d*/", "/full/max/", by)
        lic = ("Public domain" if "publicdomain/mark" in rights else
               "CC0" if "publicdomain/zero" in rights else "CC BY " + (re.findall(r"by/([\d.]+)", rights) or [""])[0])
        page = (it.get("guid") or "").split("?")[0]
        out.append({
            "source": "europeana",
            "id": f"europeana:{it.get('id', '').strip('/')}",
            "title": ((it.get("title") or [""])[0])[:200],
            "description": " ".join((it.get("dcDescription") or [])[:1])[:400],
            "date": " ".join(str(y) for y in (it.get("year") or [])),
            "page_url": page,
            "download_url": by,
            "license": lic,
            "credit": f"{(it.get('dataProvider') or ['Europeana'])[0]} via Europeana",
            "width": 0, "height": 0,
        })
    return out


SOURCES = {"commons": search_commons, "smithsonian": search_smithsonian, "europeana": search_europeana,
           "wellcome": search_wellcome, "loc": search_loc}
DEFAULT_SOURCES = ("commons", "smithsonian", "europeana", "wellcome", "loc")


DISABLED: set[str] = set()
FAILS: dict[str, int] = {}


def search_all(query: str, sources=DEFAULT_SOURCES) -> list[dict]:
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
            FAILS[s] = FAILS.get(s, 0) + 1
            if FAILS[s] >= 3:
                print(f"   ! {s} unavailable ({str(e)[:80]}), skipping it for the rest of this run")
                DISABLED.add(s)
            else:
                print(f"   ! {s} search failed for '{query}' ({str(e)[:60]})")
            lists.append([])
    out = []
    for i in range(max((len(l) for l in lists), default=0)):
        for l in lists:
            if i < len(l):
                out.append(l[i])
    return out
