# Library of Congress exchange (server ⇄ Chrome session, through this repo)

The loc.gov search is closed to our server by a Cloudflare bot check (we never try to get past it).
A person or Claude in Chrome searches loc.gov in a normal browser and hands the results back here.

## Flow
1. Server: `python run.py episodes/<ep> loc-request` → `requests/<ep>.md` (what to look for, per scene), pushed to GitHub.
2. Chrome session: open `history_channel/loc_exchange/requests/<ep>.md` on GitHub
   (https://github.com/mikagit25/forkids/tree/main/history_channel/loc_exchange), search https://www.loc.gov/photos/,
   and write `picks/<ep>.yaml` (commit to `main`; or paste the yaml into the chat with the server Claude).
3. Server: `python run.py episodes/<ep> loc-import` → checks every pick and adds it to the episode; then fetch, review.

## picks/<ep>.yaml format
```yaml
- scene: beset                       # scene id from the request
  lccn: "2013646120"                 # item page https://www.loc.gov/item/2013646120/ -> the number
  image: "https://tile.loc.gov/storage-services/service/pnp/ggbain/.../12345v.jpg"   # "Download" -> largest JPEG link
  rights: "No known restrictions on publication."                                    # copy of "Rights Advisory"
  title: "Endurance stuck fast in the ice, winter flashlight scene"
  date: "1915"
  note: "why it fits: ship in the ice at night, matches the 'long night' text"
```

## How to find era/place photos
Archives caption photos by the EVENT of the day, not "Boston street 1919". So search events of that time and place
(parades, strikes, funerals, elections, fires, openings, visits…) and pick photos that show the street, people,
vehicles, harbour we need — the event itself does not matter. Browsing a whole collection of that place and period
(e.g. Bain News Service 1915–1920 + city name) also works.

## Rules for picking (the server rejects picks that break them)
- **Rights Advisory** must say *No known restrictions on publication* or *public domain*. Anything else
  ("Rights status not evaluated", "Publication may be restricted", © …) → do not pick.
- `image` must be a `https://tile.loc.gov/…` link, the largest JPEG offered (not the thumbnail, not TIFF if > 50 MB).
- Short side at least ~900 px; no cropped thumbnails, no watermarks.
- The photo must fit the time and place of the scene (do not pass a 1930 photo for 1915).
- Prefer variety: people, places, objects, documents; no near-duplicates of one shot.
- No people's private data in notes. This repo is public.

## Newspaper clippings (Chronicling America) — picks/<ep>-news.yaml
```yaml
- scene: blast
  kind: newspaper
  image: "https://tile.loc.gov/storage-services/service/ndnp/.../0123.jp2/full/pct:100/0/default.jpg"  # full-size page JPEG
  crop: [0.05, 0.02, 0.62, 0.30]     # x0, y0, x1, y1 as fractions of the page: the headline / article only
  page_url: "https://www.loc.gov/resource/sn83045462/1917-12-06/ed-1/?sp=1"
  date: "1917-12-06"
  paper: "Evening Star (Washington, D.C.)"
  match: "the Mont-Blanc exploded"   # narrator phrase the clipping belongs to (from the request)
  note: "Front-page banner: Halifax wrecked by munitions ship explosion, hundreds dead"
```
- Pages up to 1928 only. No `rights` line needed (US newspapers before 1929 are public domain).
- The crop must contain the whole headline/article and be readable; leave a little margin.

## Photos from other archives (Nova Scotia Archives, NLM, CDC PHIL, Digital Commonwealth, NARA)
```yaml
- scene: ruins
  source: nsarchives                 # nsarchives | nlm | cdc | bpl | nara
  id: "201000123"                    # the archive's own item number (from the item page)
  image: "https://archives.novascotia.ca/.../201000123.jpg"   # largest JPEG, from the archive's own server
  page_url: "https://archives.novascotia.ca/..."
  rights: "Public domain"            # copied from the item page; NC / ND / "permission required" -> do not pick
  title: "Richmond district after the explosion"
  date: "1917-12"
  note: "why it fits"
```
