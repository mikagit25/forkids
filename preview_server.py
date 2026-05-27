"""Simple video preview server for Happy Bear Kids channel."""
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

QUEUE_DIR = Path("/opt/kids_channel/output/queue")
UPLOADED_DIR = Path("/opt/kids_channel/uploaded")
SPRITES_DIR = Path("/opt/kids_channel/assets/sprites_new")
PORT = 8899

CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; }
  h1 { text-align: center; padding: 24px; font-size: 1.6rem; color: #f9ca24; }
  .section { max-width: 1200px; margin: 0 auto 40px; padding: 0 16px; }
  h2 { font-size: 1rem; text-transform: uppercase; letter-spacing: 2px; color: #aaa;
       margin-bottom: 16px; border-bottom: 1px solid #333; padding-bottom: 8px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
  .card { background: #16213e; border-radius: 12px; overflow: hidden; border: 1px solid #0f3460; transition: transform .2s; }
  .card:hover { transform: translateY(-2px); border-color: #f9ca24; }
  .card video { width: 100%; display: block; background: #000; max-height: 200px; object-fit: contain; }
  .card .info { padding: 12px; }
  .card .title { font-size: .85rem; font-weight: bold; color: #f9ca24; margin-bottom: 4px; }
  .card .meta { font-size: .75rem; color: #888; }
  .card .size { font-size: .7rem; color: #555; margin-top: 4px; }
  .badge { display: inline-block; font-size: .65rem; padding: 2px 6px; border-radius: 4px; margin-right: 4px; font-weight: bold; }
  .badge.queue { background: #0f3460; color: #58a6ff; }
  .badge.uploaded { background: #1a3a1a; color: #56d364; }
  .badge.short { background: #3a1a3a; color: #da70d6; }
  .empty { color: #555; font-style: italic; padding: 20px; text-align: center; }
  .sprites-section { max-width: 1200px; margin: 0 auto 40px; padding: 0 16px; }
  .sprite-grid { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }
  .sprite-item { text-align: center; }
  .sprite-item img { width: 80px; height: 80px; object-fit: contain; background: rgba(255,255,255,0.1);
                     border-radius: 8px; border: 1px solid #333; }
  .sprite-item .name { font-size: .65rem; color: #888; margin-top: 4px; }
  .tabs { display: flex; gap: 8px; max-width: 1200px; margin: 0 auto 24px; padding: 0 16px; flex-wrap: wrap; }
  .tab { padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: .85rem;
         border: 1px solid #333; color: #aaa; background: transparent; }
  .tab.active { background: #f9ca24; color: #1a1a2e; border-color: #f9ca24; font-weight: bold; }
  .theme-title { margin: 16px 0 8px; color: #f9ca24; font-size: .9rem; }
"""

JS = """
function showTab(name) {
  ['queue','uploaded','sprites'].forEach(function(t) {
    document.getElementById('tab-'+t).style.display = (t===name) ? '' : 'none';
  });
  document.querySelectorAll('.tab').forEach(function(el, i) {
    el.classList.toggle('active', ['queue','uploaded','sprites'][i] === name);
  });
}
"""


def make_video_card(mp4_path: Path, badge: str) -> str:
    name = mp4_path.stem
    size_mb = mp4_path.stat().st_size / 1024 / 1024
    is_short = "short" in name.lower()
    badge_class = "short" if is_short else badge
    badge_label = "#short" if is_short else badge
    return (
        '<div class="card">'
        f'<video controls preload="none" src="/video/{badge}/{mp4_path.name}"></video>'
        '<div class="info">'
        f'<div class="title">{name.replace("_", " ")}</div>'
        f'<div class="meta"><span class="badge {badge_class}">{badge_label}</span></div>'
        f'<div class="size">{size_mb:.1f} MB</div>'
        '</div></div>'
    )


def build_html() -> str:
    queue_files = sorted(QUEUE_DIR.glob("*.mp4"))
    uploaded_files = sorted(UPLOADED_DIR.glob("*.mp4"))

    if queue_files:
        queue_html = '<div class="grid">' + "".join(make_video_card(f, "queue") for f in queue_files) + "</div>"
    else:
        queue_html = "<p class='empty'>No videos in queue</p>"

    if uploaded_files:
        uploaded_html = '<div class="grid">' + "".join(make_video_card(f, "uploaded") for f in uploaded_files) + "</div>"
    else:
        uploaded_html = "<p class='empty'>No local copies</p>"

    sprite_parts = []
    for theme_dir in sorted(SPRITES_DIR.iterdir()):
        if not theme_dir.is_dir():
            continue
        imgs = sorted(theme_dir.glob("*.png"))
        if not imgs:
            continue
        items = "".join(
            f'<div class="sprite-item"><img src="/sprite/{theme_dir.name}/{img.name}" loading="lazy">'
            f'<div class="name">{img.stem}</div></div>'
            for img in imgs
        )
        sprite_parts.append(
            f'<h3 class="theme-title">{theme_dir.name.upper()}</h3>'
            f'<div class="sprite-grid">{items}</div>'
        )
    sprites_html = "".join(sprite_parts) or "<p class='empty'>No sprites found</p>"

    qc = len(queue_files)
    uc = len(uploaded_files)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Happy Bear Kids — Preview</title>
<style>{CSS}</style>
</head>
<body>
<h1>🐻 Happy Bear Kids — Preview</h1>
<div class="tabs">
  <button class="tab active" onclick="showTab('queue')">Queue ({qc})</button>
  <button class="tab" onclick="showTab('uploaded')">Uploaded ({uc})</button>
  <button class="tab" onclick="showTab('sprites')">Sprites</button>
</div>
<div id="tab-queue" class="section">
  <h2>Videos in Queue</h2>
  {queue_html}
</div>
<div id="tab-uploaded" class="section" style="display:none">
  <h2>Uploaded Videos (local copy)</h2>
  {uploaded_html}
</div>
<div id="tab-sprites" class="sprites-section" style="display:none">
  <h2>Sprites / Images</h2>
  {sprites_html}
</div>
<script>{JS}</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress noise

    def send_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_error(404)
            return
        file_size = path.stat().st_size
        range_header = self.headers.get("Range")

        with open(path, "rb") as f:
            if range_header and range_header.startswith("bytes="):
                start, _, end = range_header[6:].partition("-")
                start = int(start) if start else 0
                end = int(end) if end else file_size - 1
                end = min(end, file_size - 1)
                length = end - start + 1
                f.seek(start)
                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(length))
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            else:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

    def do_GET(self):
        path = unquote(self.path).split("?")[0]

        if path in ("/", "/index.html"):
            html = build_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

        elif path.startswith("/video/queue/"):
            fname = path[len("/video/queue/"):]
            self.send_file(QUEUE_DIR / fname, "video/mp4")

        elif path.startswith("/video/uploaded/"):
            fname = path[len("/video/uploaded/"):]
            self.send_file(UPLOADED_DIR / fname, "video/mp4")

        elif path.startswith("/sprite/"):
            parts = path[len("/sprite/"):].split("/", 1)
            if len(parts) == 2:
                self.send_file(SPRITES_DIR / parts[0] / parts[1], "image/png")
            else:
                self.send_error(404)
        else:
            self.send_error(404)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Preview server: http://38.19.202.103:{PORT}")
    server.serve_forever()
