#!/usr/bin/env python3
"""
Weekly YouTube analytics for all three channels → what viewers search for, how they watch,
and which words belong in our titles.

Per channel (last N days, default 28, compared with the N days before):
  • totals: views, watch hours, average view duration, subscribers
  • devices: share of watch time on TV / mobile / desktop / tablet
    (high TV share ⇒ people put it on in the background → dark, slow visuals)
  • traffic sources: search, suggested, browse, external…
  • top YouTube search terms that brought viewers (the exact words people type)
  • top videos: views, average % watched, average duration, and their own top search terms
  • title keywords: words/phrases from the search terms, weighted by views, split into
    "already in our titles" and "searched but NOT in our titles" ← use these next

Output:
  reports/analytics_<YYYYMMDD>.md        human report (also short Telegram summary)
  reports/analytics_<YYYYMMDD>.json      raw numbers
  config/title_keywords_<channel>.json   keywords for generators (make_sd_video, sensory, …)

Needs the read-only analytics permission on each channel's token. If a channel was authorised
before it was added, re-run once:  python3 scripts/reauth_youtube.py --channel en|ar|id

Usage:
  python3 scripts/analytics_report.py                    # all channels, 28 days
  python3 scripts/analytics_report.py --channel sd --days 7
  python3 scripts/analytics_report.py --no-telegram
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
CONFIG = ROOT / "config"

CHANNELS = {   # key → (display name, token file, reauth flag)
    "en": ("Happy Bear Kids (EN)", ROOT / "credentials" / "youtube_token.json", "en"),
    "sd": ("Sacred Drift", ROOT / "credentials" / "youtube_token_ar.json", "ar"),
    "cc": ("Calm Classics", ROOT / "credentials" / "youtube_token_id.json", "id"),
}
STOP = set("""a an the and or of for to in on with by at from is are be it this that my your our you me i
          video videos music song songs hour hours minute minutes min hr hrs 1 2 3 4 5 6 8 10 12 24 vs no""".split())
DEVICE_NAMES = {"TV": "TV", "MOBILE": "Mobile", "DESKTOP": "Desktop", "TABLET": "Tablet", "GAME_CONSOLE": "Console",
                "UNKNOWN_PLATFORM": "Other"}
SOURCE_NAMES = {"YT_SEARCH": "YouTube search", "RELATED_VIDEO": "Suggested videos", "SUBSCRIBER": "Browse/home",
                "YT_CHANNEL": "Channel page", "EXT_URL": "External", "NO_LINK_OTHER": "Direct/other",
                "PLAYLIST": "Playlists", "YT_OTHER_PAGE": "Other YouTube", "NOTIFICATION": "Notifications",
                "SHORTS": "Shorts feed", "END_SCREEN": "End screens", "HASHTAGS": "Hashtags",
                "ADVERTISING": "Ads", "CAMPAIGN_CARD": "Campaign", "ANNOTATION": "Cards", "YT_PLAYLIST_PAGE": "Playlist page"}


class NeedsReauth(Exception):
    pass


def services(token_path: Path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    t = json.loads(token_path.read_text())
    # no explicit scopes: refresh returns whatever the user granted (asking for more would fail)
    creds = Credentials(token=t.get("access_token"), refresh_token=t["refresh_token"],
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=t["client_id"], client_secret=t["client_secret"])
    if not creds.valid:
        creds.refresh(Request())
        t["access_token"] = creds.token
        tmp = token_path.with_suffix(".tmp"); tmp.write_text(json.dumps(t, indent=2)); tmp.replace(token_path)
    return (build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False),
            build("youtube", "v3", credentials=creds, cache_discovery=False))


def q(ya, start, end, metrics, dimensions=None, filters=None, sort=None, max_results=None) -> list[dict]:
    from googleapiclient.errors import HttpError
    kw = dict(ids="channel==MINE", startDate=start, endDate=end, metrics=metrics)
    if dimensions: kw["dimensions"] = dimensions
    if filters: kw["filters"] = filters
    if sort: kw["sort"] = sort
    if max_results: kw["maxResults"] = max_results
    try:
        r = ya.reports().query(**kw).execute()
    except HttpError as e:
        msg = str(e)
        if e.resp.status in (401, 403) and ("scope" in msg.lower() or "insufficient" in msg.lower()):
            raise NeedsReauth(msg[:200])
        print(f"   ⚠ query failed ({dimensions or 'totals'}): {msg[:160]}")
        return []
    cols = [h["name"] for h in r.get("columnHeaders", [])]
    return [dict(zip(cols, row)) for row in r.get("rows", [])]


def channel_report(key: str, days: int) -> dict:
    name, token, _ = CHANNELS[key]
    ya, yt = services(token)
    end = dt.date.today() - dt.timedelta(days=2)          # analytics lag ~2 days
    start = end - dt.timedelta(days=days - 1)
    p_end = start - dt.timedelta(days=1); p_start = p_end - dt.timedelta(days=days - 1)
    S, E, PS, PE = (d.isoformat() for d in (start, end, p_start, p_end))
    base = "views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost"
    tot = (q(ya, S, E, base) or [{}])[0]
    prev = (q(ya, PS, PE, base) or [{}])[0]
    devices = q(ya, S, E, "views,estimatedMinutesWatched", "deviceType", sort="-estimatedMinutesWatched")
    sources = q(ya, S, E, "views,estimatedMinutesWatched", "insightTrafficSourceType", sort="-views")
    search = q(ya, S, E, "views,estimatedMinutesWatched", "insightTrafficSourceDetail",
               "insightTrafficSourceType==YT_SEARCH", "-views", 40)
    videos = q(ya, S, E, "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained",
               "video", sort="-views", max_results=20)
    ids = [v["video"] for v in videos]
    info = {}
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,contentDetails", id=",".join(ids[i:i + 50])).execute()
        for it in r.get("items", []):
            info[it["id"]] = {"title": it["snippet"]["title"], "published": it["snippet"]["publishedAt"][:10],
                              "duration": it["contentDetails"]["duration"]}
    for v in videos:
        v.update(info.get(v["video"], {}))
    for v in videos[:6]:                                  # what people typed to find our best videos
        v["search_terms"] = [r["insightTrafficSourceDetail"] for r in
                             q(ya, S, E, "views", "insightTrafficSourceDetail",
                               f"video=={v['video']};insightTrafficSourceType==YT_SEARCH", "-views", 10)]
        v["devices"] = {r["deviceType"]: r["estimatedMinutesWatched"] for r in
                        q(ya, S, E, "estimatedMinutesWatched", "deviceType", f"video=={v['video']}")}
    # our recent titles (to see which searched words we already use)
    ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    titles = []
    req = yt.playlistItems().list(part="snippet", playlistId=uploads, maxResults=50)
    for _ in range(2):
        if req is None:
            break
        r = req.execute()
        titles += [it["snippet"]["title"] for it in r.get("items", [])]
        req = yt.playlistItems().list_next(req, r)
    return {"key": key, "name": name, "period": [S, E], "previous": [PS, PE], "totals": tot, "prev_totals": prev,
            "devices": devices, "sources": sources, "search_terms": search, "videos": videos,
            "keywords": keywords(search, titles), "recent_titles": titles[:100]}


def keywords(search_rows: list[dict], titles: list[str]) -> dict:
    """Words and 2–3-word phrases from search terms weighted by views; split into used / missing."""
    words, phrases = Counter(), Counter()
    for r in search_rows:
        term, v = r["insightTrafficSourceDetail"].lower(), int(r["views"])
        toks = [t for t in re.findall(r"[a-z0-9]+", term) if t not in STOP and len(t) > 1]
        for t in set(toks):
            words[t] += v
        raw = re.findall(r"[a-z0-9]+", term)
        for n in (2, 3):
            for i in range(len(raw) - n + 1):
                ph = raw[i:i + n]
                if ph[0] in STOP or ph[-1] in STOP:
                    continue
                phrases[" ".join(ph)] += v
    title_text = " ".join(titles).lower()
    used = [w for w, _ in words.most_common(40) if re.search(rf"\b{re.escape(w)}", title_text)]   # prefix: nocturne ~ nocturnes
    missing = [w for w, _ in words.most_common(40) if w not in used]
    return {"words": words.most_common(40), "phrases": [p for p in phrases.most_common(25) if p[1] > 1] or
            phrases.most_common(15), "in_our_titles": used[:20], "missing_from_titles": missing[:20]}


def pct(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else "—"


def delta(a, b):
    if not b:
        return ""
    d = 100 * (a - b) / b
    return f" ({'+' if d >= 0 else ''}{d:.0f}%)"


def md_channel(R: dict) -> str:
    T, P = R["totals"], R["prev_totals"]
    hours = T.get("estimatedMinutesWatched", 0) / 60
    out = [f"## {R['name']}  ·  {R['period'][0]} → {R['period'][1]}",
           f"**Views** {int(T.get('views', 0)):,}{delta(T.get('views', 0), P.get('views', 0))} · "
           f"**Watch hours** {hours:,.0f}{delta(T.get('estimatedMinutesWatched', 0), P.get('estimatedMinutesWatched', 0))} · "
           f"**Avg view** {T.get('averageViewDuration', 0) / 60:.1f} min · "
           f"**Subs** +{int(T.get('subscribersGained', 0))} / −{int(T.get('subscribersLost', 0))}", ""]
    tm = sum(r["estimatedMinutesWatched"] for r in R["devices"])
    if tm:
        out.append("**Devices (watch time):** " + " · ".join(
            f"{DEVICE_NAMES.get(r['deviceType'], r['deviceType'])} {pct(r['estimatedMinutesWatched'], tm)}"
            for r in R["devices"]))
        tv = next((r["estimatedMinutesWatched"] for r in R["devices"] if r["deviceType"] == "TV"), 0)
        if tm and tv / tm >= 0.2:
            out.append(f"> 📺 TV is {pct(tv, tm)} of watch time — viewers play it in the background on a TV: "
                       "dark, slow visuals and long durations fit this audience.")
    tv_ = sum(r["views"] for r in R["sources"])
    if tv_:
        out.append("**Traffic:** " + " · ".join(f"{SOURCE_NAMES.get(r['insightTrafficSourceType'], r['insightTrafficSourceType'])} "
                                              f"{pct(r['views'], tv_)}" for r in R["sources"][:6]))
    out.append("")
    if R["search_terms"]:
        out.append("**What people searched (YouTube search → our videos):**")
        out += [f"{i + 1}. {r['insightTrafficSourceDetail']} — {int(r['views'])} views"
                for i, r in enumerate(R["search_terms"][:20])]
        out.append("")
    K = R["keywords"]
    if K["words"]:
        out.append("**Title keywords** (by search views): " + ", ".join(f"{w} ({v})" for w, v in K["words"][:15]))
        if K["phrases"]:
            out.append("**Phrases:** " + ", ".join(f"“{p}”" for p, _ in K["phrases"][:10]))
        if K["missing_from_titles"]:
            out.append("**➕ Searched but NOT in our titles — try them:** " + ", ".join(K["missing_from_titles"][:12]))
        out.append("")
    if R["videos"]:
        out.append("| Video | Views | Avg % watched | Avg min | TV share | Found by |")
        out.append("|---|---:|---:|---:|---:|---|")
        for v in R["videos"][:12]:
            dv = v.get("devices") or {}
            tvs = pct(dv.get("TV", 0), sum(dv.values())) if dv else ""
            st = ", ".join((v.get("search_terms") or [])[:3])
            out.append(f"| {v.get('title', v['video'])[:70]} | {int(v['views']):,} | {v['averageViewPercentage']:.0f}% | "
                       f"{v['averageViewDuration'] / 60:.1f} | {tvs} | {st} |")
        out.append("")
    return "\n".join(out)


def telegram_summary(reports: list[dict]) -> str:
    lines = ["📊 <b>Weekly YouTube report</b>"]
    for R in reports:
        if "error" in R:
            lines.append(f"\n<b>{R['name']}</b>: ⚠ {R['error']}")
            continue
        T = R["totals"]; tm = sum(r["estimatedMinutesWatched"] for r in R["devices"])
        tv = next((r["estimatedMinutesWatched"] for r in R["devices"] if r["deviceType"] == "TV"), 0)
        top = ", ".join(r["insightTrafficSourceDetail"] for r in R["search_terms"][:3])
        miss = ", ".join(R["keywords"]["missing_from_titles"][:5])
        lines.append(f"\n<b>{R['name']}</b>: {int(T.get('views', 0)):,} views{delta(T.get('views', 0), R['prev_totals'].get('views', 0))}, "
                     f"{T.get('estimatedMinutesWatched', 0) / 60:,.0f} h, TV {pct(tv, tm)}"
                     + (f"\n🔎 {top}" if top else "") + (f"\n➕ {miss}" if miss else ""))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="YouTube analytics report for our channels")
    ap.add_argument("--channel", choices=["all"] + list(CHANNELS), default="all")
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--no-telegram", action="store_true")
    a = ap.parse_args()
    keys = list(CHANNELS) if a.channel == "all" else [a.channel]
    REPORTS.mkdir(exist_ok=True)
    out, md = [], [f"# YouTube analytics — {dt.date.today():%Y-%m-%d} (last {a.days} days)", ""]
    for k in keys:
        name, token, flag = CHANNELS[k]
        print(f"📈 {name} …")
        if not token.exists():
            out.append({"key": k, "name": name, "error": "no token"}); continue
        try:
            R = channel_report(k, a.days)
        except NeedsReauth:
            err = f"needs analytics permission — run: python3 scripts/reauth_youtube.py --channel {flag}"
            print("   ⚠ " + err); out.append({"key": k, "name": name, "error": err})
            md += [f"## {name}", f"⚠ {err}", ""]; continue
        out.append(R); md.append(md_channel(R))
        (CONFIG / f"title_keywords_{k}.json").write_text(json.dumps(
            {"updated": dt.date.today().isoformat(), "period": R["period"], **R["keywords"],
             "top_search_terms": [r["insightTrafficSourceDetail"] for r in R["search_terms"][:25]]},
            indent=1, ensure_ascii=False))
    stamp = f"{dt.date.today():%Y%m%d}"
    (REPORTS / f"analytics_{stamp}.md").write_text("\n".join(md))
    (REPORTS / f"analytics_{stamp}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    print(f"✅ reports/analytics_{stamp}.md")
    if not a.no_telegram:
        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            from reauth_youtube import send_telegram
            send_telegram(telegram_summary(out))
        except Exception as e:                            # report is saved either way
            print(f"   (telegram skipped: {e})")


if __name__ == "__main__":
    main()
