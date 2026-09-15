#!/usr/bin/env python3
"""Media file browser with upload — kids_channel assets."""

import http.server
import socketserver
import os
import io
import mimetypes
import email.parser
import email.policy
import yaml
import html as htmllib
import json
from pathlib import Path
from urllib.parse import unquote, quote, parse_qs, urlparse
from datetime import datetime

ROOT = Path('/opt/kids_channel')
PORT = 8888
PASSWORD = "bear2026"
BASE = "/files"  # nginx proxy prefix — all generated URLs include this

BLOCKED = {'credentials', '.git', '__pycache__', 'node_modules', '.claude'}
MEDIA_EXTS = {'.mp3', '.mp4', '.wav', '.ogg', '.png', '.jpg', '.jpeg', '.webp', '.gif'}
AUDIO_EXTS = {'.mp3', '.wav', '.ogg'}
VIDEO_EXTS = {'.mp4', '.webm'}
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

QUICK_LINKS = [
    ('🔮 SD Audio Library', 'sacred_drift/audio/library'),
    ('📤 SD Uploads',       'sacred_drift/audio/uploads'),
    ('🎬 SD Queue',         'sacred_drift/output/queue'),
    ('─────────────', None),
    ('🎬 CC Queue',         'output/queue_id'),
    ('🐻 EN Queue',         'output/queue'),
    ('🎵 Suno Kids',        'assets/audio/suno'),
    ('🎻 Classical',        'assets/music/classical/Music'),
    ('📁 All Assets',       'assets'),
]

UPLOAD_GUIDES = [
    ('📋 CC Upload Guide', '/queue?q=id'),
    ('📋 EN Upload Guide', '/queue?q=en'),
]

def fmt_size(n):
    for unit in ['B','KB','MB','GB']:
        if n < 1024: return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def fmt_date(ts):
    return datetime.fromtimestamp(ts).strftime('%d.%m %H:%M')

def is_blocked(p: Path) -> bool:
    return any(part in BLOCKED for part in p.parts)

def safe_path(rel: str) -> Path | None:
    p = (ROOT / rel).resolve()
    if not str(p).startswith(str(ROOT)):
        return None
    if is_blocked(p.relative_to(ROOT)):
        return None
    return p

HTML_HEAD = """<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kids Channel · Media</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#0d0d0d;color:#ddd;display:flex;flex-direction:column;height:100vh}
/* TOP BAR */
.topbar{background:#111;border-bottom:1px solid #222;padding:10px 16px;
        display:flex;align-items:center;gap:12px;flex-shrink:0}
.topbar h1{font-size:17px;font-weight:600;color:#fff;white-space:nowrap}
.topbar input[type=search]{flex:1;padding:7px 12px;background:#1a1a1a;border:1px solid #333;
  border-radius:6px;color:#ddd;font-size:13px;min-width:0}
.topbar input:focus{outline:none;border-color:#555}
/* LAYOUT */
.layout{display:flex;flex:1;overflow:hidden}
/* SIDEBAR */
.sidebar{width:200px;flex-shrink:0;background:#111;border-right:1px solid #1e1e1e;
         overflow-y:auto;padding:12px 0}
.sidebar-title{font-size:11px;font-weight:600;color:#555;padding:8px 14px 4px;
               text-transform:uppercase;letter-spacing:.06em}
.sidebar a{display:block;padding:6px 14px;font-size:13px;color:#999;
           text-decoration:none;border-radius:0;white-space:nowrap;overflow:hidden;
           text-overflow:ellipsis}
.sidebar a:hover{background:#1a1a1a;color:#ddd}
.sidebar a.active{background:#1a2040;color:#aaf;border-right:2px solid #558}
/* MAIN */
.main{flex:1;overflow-y:auto;padding:0}
/* BREADCRUMB */
.breadcrumb{padding:10px 16px;font-size:13px;color:#666;background:#111;
            border-bottom:1px solid #1a1a1a;display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.breadcrumb a{color:#889;text-decoration:none}.breadcrumb a:hover{color:#aaf}
.breadcrumb span{color:#444}
/* UPLOAD */
.upload-bar{padding:10px 16px;background:#0f1a0f;border-bottom:1px solid #1a2a1a;
            display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.upload-bar label{font-size:13px;color:#8a8}
.upload-bar input[type=file]{font-size:12px;color:#aaa;flex:1;min-width:0}
.btn{padding:6px 14px;border-radius:5px;font-size:12px;border:none;cursor:pointer;
     font-family:inherit;text-decoration:none;display:inline-block}
.btn-upload{background:#1a3a1a;color:#8e8;border:1px solid #2a5a2a}
.btn-upload:hover{background:#2a4a2a}
.btn-dl{background:#1a2a4a;color:#acd;border:1px solid #2a3a6a;white-space:nowrap}
.btn-dl:hover{background:#253570}
/* FILE TABLE */
.file-table{width:100%;border-collapse:collapse}
.file-table th{font-size:11px;font-weight:600;color:#555;text-transform:uppercase;
               padding:8px 16px;text-align:left;border-bottom:1px solid #1a1a1a;
               position:sticky;top:0;background:#0d0d0d;z-index:1}
.file-table td{padding:6px 16px;border-bottom:1px solid #161616;vertical-align:middle}
.file-table tr:hover td{background:#131313}
.fname{font-size:13px;color:#ccc;word-break:break-all}
.fname a{color:#ccc;text-decoration:none}.fname a:hover{color:#aaf}
.fsize{font-size:12px;color:#555;white-space:nowrap}
.fdate{font-size:12px;color:#444;white-space:nowrap}
.factions{text-align:right;white-space:nowrap}
/* PLAYER */
audio{width:100%;height:32px;margin-top:4px;display:block}
.thumb-preview{max-height:40px;max-width:80px;border-radius:4px;vertical-align:middle;margin-right:8px}
/* DIRS */
.dir-row td{padding:5px 16px}
.dir-icon{color:#885;font-size:14px}
.dir-link{color:#998;text-decoration:none;font-size:13px}
.dir-link:hover{color:#ccb}
/* STATS */
.stats{padding:8px 16px;font-size:12px;color:#444;border-top:1px solid #1a1a1a;
       background:#0d0d0d;flex-shrink:0}
/* LOGIN */
.login-wrap{display:flex;align-items:center;justify-content:center;height:100vh;
            background:#0d0d0d}
.login-box{background:#161616;padding:36px 40px;border-radius:14px;
           border:1px solid #2a2a2a;text-align:center;width:280px}
.login-box h2{margin-bottom:20px;color:#fff;font-size:18px}
.login-box input{width:100%;padding:10px 14px;background:#111;border:1px solid #333;
  color:#ddd;border-radius:7px;font-size:14px;margin-bottom:12px}
.login-box button{width:100%;padding:10px;background:#2a3a8a;color:#ddd;border:none;
  border-radius:7px;font-size:14px;cursor:pointer}
.upload-progress{font-size:12px;color:#6a6;padding:4px 0}
.upload-bar-inner{display:flex;align-items:center;gap:10px;flex-wrap:wrap;width:100%}
.uprog-track{height:4px;background:#1a3a1a;border-radius:2px;flex:1;min-width:80px;overflow:hidden}
.uprog-fill{height:100%;background:#4a8;border-radius:2px;width:0;transition:width .2s}
</style>
</head><body>"""

JS = """<script>
// Search filter
const searchInput = document.getElementById('search');
if(searchInput){
  searchInput.addEventListener('input', function(){
    const q = this.value.toLowerCase();
    document.querySelectorAll('.file-table tbody tr').forEach(tr=>{
      const name = (tr.getAttribute('data-name')||'').toLowerCase();
      tr.style.display = name.includes(q) ? '' : 'none';
    });
  });
}

// Sequential file uploader — one file at a time via fetch()
const fileInput = document.getElementById('upload-files');
const uploadBtn = document.getElementById('upload-btn');
const progText  = document.getElementById('upload-prog-text');
const progFill  = document.getElementById('upload-prog-fill');

function getUploadDir(){
  const m = location.search.match(/[?&]dir=([^&]*)/);
  return m ? decodeURIComponent(m[1]) : '';
}

async function uploadFile(file, dir, idx, total){
  const fname = encodeURIComponent(file.name);
  const url   = BASE + '/upload?dir=' + encodeURIComponent(dir) + '&filename=' + fname;
  progText.textContent = idx + '/' + total + ' — ' + file.name.slice(0,40);
  progFill.style.width = Math.round((idx-1)/total*100) + '%';
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/octet-stream'},
      body: file,
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return true;
  } catch(e){
    progText.textContent = '❌ Ошибка: ' + file.name + ' — ' + e.message;
    progText.style.color = '#f66';
    return false;
  }
}

if(uploadBtn){
  uploadBtn.addEventListener('click', async function(){
    const files = fileInput.files;
    if(!files || !files.length) return;
    const dir   = getUploadDir();
    const total = files.length;
    uploadBtn.disabled = true;
    fileInput.disabled = true;
    progText.style.color = '#6a6';
    let ok = 0;
    for(let i=0; i<total; i++){
      const success = await uploadFile(files[i], dir, i+1, total);
      if(success) ok++;
    }
    progFill.style.width = '100%';
    progText.textContent = '✓ Загружено ' + ok + '/' + total + ' файлов. Обновляем...';
    setTimeout(() => location.reload(), 800);
  });
}
</script>"""

def render_queue(queue_dir: Path, queue_name: str) -> bytes:
    """Render upload guide page — title + description + tags for each video."""
    videos = []
    for mp4 in sorted(queue_dir.glob('*.mp4')):
        if mp4.name.startswith('short_') or mp4.name.startswith('kw_short'):
            continue  # skip shorts for now
        stem = mp4.stem
        meta_path = queue_dir / f'meta_{stem}.yaml'
        thumb_path = queue_dir / f'thumb_{stem}.png'
        if not meta_path.exists():
            continue
        try:
            meta = yaml.safe_load(meta_path.read_text()) or {}
        except Exception:
            continue
        if meta.get('youtube_id'):
            continue  # already uploaded
        if meta.get('upload_blocked'):
            continue
        frel_mp4 = str(mp4.relative_to(ROOT))
        frel_thumb = str(thumb_path.relative_to(ROOT)) if thumb_path.exists() else None
        videos.append({
            'name': mp4.name,
            'size': fmt_size(mp4.stat().st_size),
            'title': meta.get('title', ''),
            'description': meta.get('description', ''),
            'tags': ', '.join(meta.get('tags', [])),
            'mp4_url': f'{BASE}/file/{quote(frel_mp4)}',
            'thumb_url': f'{BASE}/file/{quote(frel_thumb)}' if frel_thumb else '',
        })

    B = BASE
    cards = ''
    for idx, v in enumerate(videos):
        title_esc = htmllib.escape(v['title'])
        desc_esc  = htmllib.escape(v['description'])
        tags_esc  = htmllib.escape(v['tags'])
        title_js  = json.dumps(v['title'])
        desc_js   = json.dumps(v['description'])
        tags_js   = json.dumps(v['tags'])
        thumb_html = (f'<img src="{v["thumb_url"]}" style="width:160px;height:90px;'
                      f'object-fit:cover;border-radius:6px;flex-shrink:0">'
                      if v['thumb_url'] else
                      '<div style="width:160px;height:90px;background:#1a1a1a;border-radius:6px;flex-shrink:0"></div>')
        dl_thumb = (f'<a class="btn btn-dl" href="{v["thumb_url"]}" download="thumb.png">⬇ Обложка</a>'
                    if v['thumb_url'] else '')
        cards += f"""
<div class="qcard">
  <div style="display:flex;gap:14px;align-items:flex-start">
    {thumb_html}
    <div style="flex:1;min-width:0">
      <div style="font-size:12px;color:#555;margin-bottom:3px">{v['name']} · {v['size']}</div>
      <div style="font-size:15px;font-weight:600;color:#fff;margin-bottom:10px">{title_esc}</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-copy" onclick="copyText({title_js}, this)">📋 Заголовок</button>
        <button class="btn btn-copy" onclick="copyText({desc_js}, this)">📋 Описание</button>
        <button class="btn btn-copy" onclick="copyText({tags_js}, this)">📋 Теги</button>
        <button class="btn btn-preview" onclick="showModal({idx})">👁 Просмотр</button>
        <a class="btn btn-dl" href="{v['mp4_url']}" download="{v['name']}">⬇ MP4</a>
        {dl_thumb}
      </div>
    </div>
  </div>
  <div id="modal-desc-{idx}" style="display:none">{desc_esc}</div>
  <div id="modal-tags-{idx}" style="display:none">{tags_esc}</div>
</div>"""

    if not cards:
        cards = '<div style="color:#555;padding:20px">Нет видео готовых к загрузке</div>'

    active_id = f'/queue?q={"id" if "queue_id" in str(queue_dir) else "en"}'
    sidebar = build_sidebar(active_guide=active_id)

    page = HTML_HEAD + f"""
<style>
.qcard{{background:#161616;border:1px solid #252525;border-radius:10px;padding:16px;margin-bottom:10px}}
.qcard:hover{{border-color:#333}}
.btn-copy{{background:#1a1a3a;color:#aaf;border:1px solid #2a2a6a;cursor:pointer}}
.btn-copy:hover{{background:#2a2a5a}}
.btn-copy.copied{{background:#1a3a1a;color:#8e8;border-color:#2a5a2a}}
.btn-preview{{background:#1a2a1a;color:#aca;border:1px solid #2a5a2a;cursor:pointer}}
.btn-preview:hover{{background:#223a22}}
/* Modal */
.modal-overlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:1000;align-items:center;justify-content:center}}
.modal-overlay.open{{display:flex}}
.modal-box{{background:#1a1a1a;border:1px solid #333;border-radius:12px;width:min(700px,95vw);
            max-height:85vh;display:flex;flex-direction:column;overflow:hidden}}
.modal-head{{padding:14px 18px;border-bottom:1px solid #2a2a2a;display:flex;justify-content:space-between;align-items:center}}
.modal-head h3{{font-size:15px;color:#fff;font-weight:600;margin:0}}
.modal-close{{background:none;border:none;color:#666;font-size:20px;cursor:pointer;padding:0 4px;line-height:1}}
.modal-close:hover{{color:#fff}}
.modal-body{{padding:16px 18px;overflow-y:auto;flex:1}}
.modal-body pre{{white-space:pre-wrap;font-size:13px;color:#ccc;font-family:inherit;line-height:1.6}}
.modal-tags{{margin-top:14px;padding-top:14px;border-top:1px solid #222;font-size:12px;color:#777}}
.modal-foot{{padding:12px 18px;border-top:1px solid #222;display:flex;gap:8px}}
</style>

<!-- Modal -->
<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal-box">
    <div class="modal-head">
      <h3 id="modal-title"></h3>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <pre id="modal-text"></pre>
      <div class="modal-tags"><b>Теги:</b> <span id="modal-tags-text"></span></div>
    </div>
    <div class="modal-foot">
      <button class="btn btn-copy" id="modal-copy-desc" onclick="copyModal()">📋 Копировать описание</button>
      <button class="btn btn-copy" id="modal-copy-tags" onclick="copyModalTags()">📋 Копировать теги</button>
    </div>
  </div>
</div>

<div class="topbar">
  <h1>🐻 Kids Channel</h1>
  <small style="color:#888">{queue_name} · {len(videos)} видео готовы к загрузке</small>
</div>
<div class="layout">
  <div class="sidebar">{sidebar}</div>
  <div class="main" style="padding:16px 20px;overflow-y:auto">{cards}</div>
</div>
<script>
let _curDesc = '', _curTags = '';
function showModal(idx) {{
  const title = document.querySelector(`[onclick="showModal(${{idx}})"]`)
    .closest('.qcard').querySelector('[style*="font-weight:600"]').textContent;
  _curDesc = document.getElementById('modal-desc-' + idx).textContent;
  _curTags = document.getElementById('modal-tags-' + idx).textContent;
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-text').textContent = _curDesc;
  document.getElementById('modal-tags-text').textContent = _curTags;
  document.getElementById('modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}}
function closeModal() {{
  document.getElementById('modal').classList.remove('open');
  document.body.style.overflow = '';
}}
document.addEventListener('keydown', e => {{ if(e.key==='Escape') closeModal(); }});
function copyText(text, btn) {{
  navigator.clipboard.writeText(text).then(() => {{
    const orig = btn.textContent;
    btn.textContent = '✓ Скопировано';
    btn.classList.add('copied');
    setTimeout(() => {{ btn.textContent = orig; btn.classList.remove('copied'); }}, 1500);
  }});
}}
function copyModal() {{ copyText(_curDesc, document.getElementById('modal-copy-desc')); }}
function copyModalTags() {{ copyText(_curTags, document.getElementById('modal-copy-tags')); }}
</script>
</body></html>"""
    return page.encode('utf-8')


def build_sidebar(active_dir: str = '', active_guide: str = '') -> str:
    B = BASE
    s = '<div class="sidebar-title">📁 Файлы</div>'
    for label, path in QUICK_LINKS:
        if path is None:
            s += f'<div style="padding:2px 14px;color:#333;font-size:11px;user-select:none">{label}</div>'
            continue
        active = 'active' if active_dir == path else ''
        s += f'<a class="{active}" href="{B}/?dir={quote(path)}">{label}</a>'
    s += '<div class="sidebar-title" style="margin-top:10px">📋 Upload Guide</div>'
    for label, href in UPLOAD_GUIDES:
        active = 'active' if active_guide == href else ''
        s += f'<a class="{active}" href="{B}{href}">{label}</a>'
    return s


def render_login():
    return (HTML_HEAD + f"""
<div class="login-wrap">
<div class="login-box">
  <h2>🐻 Kids Channel</h2>
  <form method="get" action="{BASE}/">
    <input type="password" name="pw" placeholder="Пароль" autofocus autocomplete="current-password">
    <button type="submit">Войти</button>
  </form>
</div>
</div></body></html>""").encode()

def render_dir(rel: str, cur_path: Path, query: str = '') -> bytes:
    B = BASE
    # Breadcrumb
    parts = Path(rel).parts if rel else ()
    crumbs = f'<a href="{B}/?dir=">ROOT</a>'
    for i, part in enumerate(parts):
        sub = '/'.join(parts[:i+1])
        crumbs += f' <span>/</span> <a href="{B}/?dir={quote(sub)}">{part}</a>'

    sidebar = build_sidebar(active_dir=rel)

    # List contents
    dirs, files = [], []
    if cur_path.exists():
        for item in sorted(cur_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if item.name.startswith('.') or item.name in BLOCKED:
                continue
            if item.is_dir():
                dirs.append(item)
            elif item.suffix.lower() in MEDIA_EXTS:
                files.append(item)

    if query:
        files = [f for f in files if query.lower() in f.name.lower()]

    # Directory rows
    dir_rows = ''
    for d in dirs:
        drel = str(d.relative_to(ROOT))
        count = sum(1 for x in d.iterdir() if x.suffix.lower() in MEDIA_EXTS) if d.exists() else 0
        dir_rows += f"""<tr class="dir-row" data-name="{d.name}">
          <td colspan="3"><span class="dir-icon">📁</span>
            <a class="dir-link" href="{B}/?dir={quote(drel)}">{d.name}/</a>
            <span style="color:#443;font-size:11px;margin-left:6px">{count} media</span></td>
          <td></td></tr>"""

    # File rows
    file_rows = ''
    total_size = 0
    for f in files:
        stat = f.stat()
        total_size += stat.st_size
        frel = str(f.relative_to(ROOT))
        dl_url = f"{B}/file/{quote(frel)}"
        ext = f.suffix.lower()

        if ext in IMAGE_EXTS:
            preview = f'<img class="thumb-preview" src="{dl_url}" loading="lazy">'
            player = ''
        else:
            preview = ''
            player = ''

        if ext in AUDIO_EXTS:
            player = f'<audio controls preload="none" src="{dl_url}"></audio>'
        elif ext in VIDEO_EXTS:
            player = f'<video controls preload="none" src="{dl_url}" style="width:100%;max-height:120px;margin-top:4px;display:block;border-radius:4px"></video>'

        file_rows += f"""<tr data-name="{f.name}">
          <td class="fname">{preview}<a href="{dl_url}">{f.name}</a>{player}</td>
          <td class="fsize">{fmt_size(stat.st_size)}</td>
          <td class="fdate">{fmt_date(stat.st_mtime)}</td>
          <td class="factions"><a class="btn btn-dl" href="{dl_url}" download="{f.name}">⬇</a></td>
        </tr>"""

    if not dirs and not files:
        file_rows = '<tr><td colspan="4" style="color:#444;padding:20px 16px">Нет медиа-файлов</td></tr>'

    dir_enc = quote(rel)
    stats_txt = f"{len(files)} файлов · {fmt_size(total_size)}" if files else "Нет файлов"

    page = HTML_HEAD + f"""
<div class="topbar">
  <h1>🐻 Kids Channel</h1>
  <input type="search" id="search" placeholder="Поиск по имени..." value="{query}">
</div>
<div class="layout">
  <div class="sidebar">{sidebar}</div>
  <div class="main" style="display:flex;flex-direction:column">
    <div class="breadcrumb">{crumbs}</div>
    <div class="upload-bar">
      <div class="upload-bar-inner">
        <label>📤 Загрузить:</label>
        <input type="file" id="upload-files" multiple style="flex:1;min-width:0;font-size:12px;color:#aaa">
        <button id="upload-btn" class="btn btn-upload">Загрузить</button>
        <span id="upload-prog-text" class="upload-progress"></span>
      </div>
      <div class="uprog-track" style="margin-top:4px">
        <div class="uprog-fill" id="upload-prog-fill"></div>
      </div>
    </div>
    <script>const BASE="{B}";</script>
    <div style="flex:1;overflow-y:auto">
      <table class="file-table">
        <thead><tr>
          <th>Файл</th><th>Размер</th><th>Дата</th><th></th>
        </tr></thead>
        <tbody>{dir_rows}{file_rows}</tbody>
      </table>
    </div>
    <div class="stats">{stats_txt} &nbsp;·&nbsp; <code>{cur_path}</code></div>
  </div>
</div>
{JS}</body></html>"""
    return page.encode('utf-8')

def parse_multipart(rfile, content_type, content_length):
    """Parse multipart/form-data, return list of (filename, data) tuples."""
    boundary = None
    for part in content_type.split(';'):
        part = part.strip()
        if part.startswith('boundary='):
            boundary = part[9:].strip('"')
    if not boundary:
        return []

    raw = rfile.read(content_length)
    results = []
    sep = f'--{boundary}'.encode()
    end = f'--{boundary}--'.encode()

    parts = raw.split(sep)
    for chunk in parts:
        if not chunk or chunk == b'--\r\n' or chunk.startswith(b'--'):
            continue
        if b'\r\n\r\n' not in chunk:
            continue
        header_raw, body = chunk.split(b'\r\n\r\n', 1)
        if body.endswith(b'\r\n'):
            body = body[:-2]
        header_str = header_raw.decode('utf-8', errors='replace')
        filename = None
        for line in header_str.splitlines():
            if 'Content-Disposition' in line and 'filename=' in line:
                for seg in line.split(';'):
                    seg = seg.strip()
                    if seg.startswith('filename='):
                        filename = seg[9:].strip('"')
        if filename and body:
            results.append((filename, body))
    return results


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def authed(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if qs.get('pw', [''])[0] == PASSWORD:
            return True
        return f'pw={PASSWORD}' in self.headers.get('Cookie', '')

    def set_cookie_header(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        return qs.get('pw', [''])[0] == PASSWORD

    def do_GET(self):
        if not self.authed():
            body = render_login()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
            return

        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        # Strip BASE prefix so handler works both direct and via nginx proxy
        path = parsed.path
        if path.startswith(BASE):
            path = path[len(BASE):] or '/'
        need_cookie = self.set_cookie_header()

        # Upload guide page
        if path in ('/queue', '/queue/'):
            q = qs.get('q', ['id'])[0]
            queue_map = {
                'id': (ROOT / 'output/queue_id', 'Calm Classics'),
                'en': (ROOT / 'output/queue',    'EN Kids'),
            }
            qdir, qname = queue_map.get(q, queue_map['id'])
            body = render_queue(qdir, qname)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(body))
            if need_cookie:
                self.send_header('Set-Cookie', f'pw={PASSWORD}; Path=/; Max-Age=604800')
            self.end_headers()
            self.wfile.write(body)
            return

        # Serve file
        if path.startswith('/file/'):
            rel = unquote(path[6:])
            full = safe_path(rel)
            if not full or not full.is_file():
                self.send_error(404)
                return
            mime = mimetypes.guess_type(str(full))[0] or 'application/octet-stream'
            size = full.stat().st_size
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', size)
            # Inline for audio/video/image, attachment for download
            if full.suffix.lower() in {'.mp4', '.mp3', '.wav', '.ogg', '.png', '.jpg', '.jpeg', '.webp', '.gif'}:
                self.send_header('Content-Disposition', f'inline; filename="{full.name}"')
            else:
                self.send_header('Content-Disposition', f'attachment; filename="{full.name}"')
            if need_cookie:
                self.send_header('Set-Cookie', f'pw={PASSWORD}; Path=/; Max-Age=604800')
            self.end_headers()
            with open(full, 'rb') as f:
                while chunk := f.read(1 << 20):
                    self.wfile.write(chunk)
            return

        # Directory browser
        rel = qs.get('dir', [''])[0]
        query = qs.get('q', [''])[0]
        if rel:
            cur = safe_path(rel)
            if not cur or not cur.exists():
                cur = ROOT
                rel = ''
        else:
            cur = ROOT

        body = render_dir(rel, cur, query)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(body))
        if need_cookie:
            self.send_header('Set-Cookie', f'pw={PASSWORD}; Path=/; Max-Age=604800')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not self.authed():
            self.send_error(403)
            return

        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        post_path = parsed.path
        if post_path.startswith(BASE):
            post_path = post_path[len(BASE):] or '/'

        if post_path == '/upload':
            rel  = qs.get('dir', [''])[0]
            dest = safe_path(rel) if rel else None
            if not dest or not dest.is_dir():
                self.send_error(400, 'Invalid directory')
                return

            ct = self.headers.get('Content-Type', '')
            cl = int(self.headers.get('Content-Length', 0))

            if 'octet-stream' in ct:
                # New JS uploader: single file per request, name in ?filename=
                raw_fname = qs.get('filename', [''])[0]
                filename  = Path(raw_fname).name if raw_fname else None
                if not filename:
                    self.send_error(400, 'Missing filename')
                    return
                out = dest / filename
                # Stream straight to disk — no RAM spike
                remaining = cl
                with open(out, 'wb') as fh:
                    while remaining > 0:
                        chunk = self.rfile.read(min(65536, remaining))
                        if not chunk:
                            break
                        fh.write(chunk)
                        remaining -= len(chunk)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                body = b'{"ok":true}'
                self.send_header('Content-Length', len(body))
                self.end_headers()
                self.wfile.write(body)
            else:
                # Legacy multipart fallback
                files = parse_multipart(self.rfile, ct, cl)
                for filename, data in files:
                    filename = Path(filename).name
                    if filename:
                        (dest / filename).write_bytes(data)
                dir_enc = quote(rel)
                self.send_response(303)
                self.send_header('Location', f'{BASE}/?dir={dir_enc}')
                self.end_headers()
            return

        self.send_error(404)


class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == '__main__':
    mimetypes.add_type('video/mp4', '.mp4')
    mimetypes.add_type('audio/mpeg', '.mp3')
    with ThreadedServer(('', PORT), Handler) as srv:
        print(f"http://38.19.202.103:{PORT}  pw: {PASSWORD}")
        srv.serve_forever()
