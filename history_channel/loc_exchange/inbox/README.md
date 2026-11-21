# inbox: images the server cannot download itself

Some archives (NLM Digital Collections: AWS WAF bot check) only serve images to a normal browser.
We never try to pass such checks from the server. Instead:

1. In Chrome open each NLM item page from `../picks/<ep>.yaml` and press **Download → JPEG (largest)**.
2. Keep the archive id in the file name (the default NLM name already has it, e.g. `nlm_nlmuid-101392841-img.jpg`).
3. Upload them here on GitHub: this folder → **Add file → Upload files** → drag all the JPEGs → Commit
   (subfolders per episode are fine: `inbox/tuberculosis/…`).

The server matches files to picks by the id in the file name; fetch then uses the local file.
Rights were already checked when the pick was made (public domain / no known restrictions only).

## Easier: the file browser (no GitHub needed)
https://medmind.pro/files → sidebar **📷 Archive Tales фото** → open the episode folder (tuberculosis, yellow-fever,
smallpox, other) → choose files → «Загрузить». Files go straight to this folder on the server.
