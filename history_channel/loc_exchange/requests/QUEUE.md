# Queue for the Chrome session (updated 2026-11-20)

Work top to bottom. One episode = one commit `loc_exchange: <ep> picks (N)`; then tell the server Claude
(paste the commit id in the chat). Format and rights rules: `../README.md` — the server rejects anything else.

| # | Episode | Request | Picks file | What matters most |
|---|---|---|---|---|
| ✅ | endurance-1914 | endurance-1914.md | picks/endurance-1914.yaml | done (14) |
| ✅ | halifax-1917 news | halifax-1917-news.md | picks/halifax-1917-news.yaml | done (9) |
| ✅ | molasses-1919 news | molasses-1919-news.md | picks/molasses-1919-news.yaml | done (9) |
| 1 | **halifax-1917** photos | halifax-1917.md | picks/halifax-1917.yaml | ruins of Richmond district, relief trains, Boston relief, tents/shelters, blizzard. LoC: Bain, Harris & Ewing, American Red Cross collection |
| 2 | **tuberculosis** | tuberculosis.md | picks/tuberculosis.yaml | sanatoriums, open-air schools, porch "cure" beds, Christmas Seals, Red Cross / public health posters (LoC "Posters" + "Prints & Photographs"), Koch |
| 3 | **molasses-1919** photos | molasses-1919.md | picks/molasses-1919.yaml | Boston North End / Commercial Street / elevated railway 1910s, horses & wagons, harbour, Purity tank if any |
| 4 | **yellow-fever** | yellow-fever.md | picks/yellow-fever.yaml | Walter Reed, Havana 1900, Camp Lazear, Panama Canal (Gorgas, fumigation brigades, Culebra Cut), Memphis/New Orleans 1878 prints |
| 5 | **smallpox** | smallpox.md | picks/smallpox.yaml | vaccination scenes 1900–1950s, quarantine signs, pest houses, Jenner prints, WHO eradication era (only if "No known restrictions") |

## Other sites worth a look in Chrome (same rules: PD / CC0 / CC BY / "No known restrictions" only)
- **Nova Scotia Archives** (archives.novascotia.ca) — the largest Halifax explosion photo set. Check the rights line
  of each image; if it says the photo is public domain / no restrictions, add it to picks/halifax-1917.yaml with
  `source: "nsarchives"`, `page_url`, `image` (largest JPEG link), `rights` (copied) — the server will check it by hand
  (no lccn needed for this source).
- **Digital Commonwealth / Boston Public Library** — molasses flood. ⚠️ The Leslie Jones collection is CC BY-NC-ND →
  NOT allowed. Only items marked public domain / no known restrictions.
- **National Library of Medicine Digital Collections** (collections.nlm.nih.gov) — tuberculosis, yellow fever, smallpox
  posters and photos; most are public domain (check "Rights").
- **CDC Public Health Image Library** (phil.cdc.gov) — smallpox eradication photos; only those marked "public domain".

## Not needed
- AI images of any kind. Modern photos (after the episode's era) unless a scene says "today".
