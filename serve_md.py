#!/usr/bin/env python3
"""Explorador de archivos con columnas ordenables. Renderiza .md como HTML."""

import http.server
import os
import re
import html as html_mod
import json
import csv
import io
import urllib.parse
from datetime import datetime
import duckdb

ROOT_NAME = "/"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMPL_DIR = os.path.join(SCRIPT_DIR, "templates")


def load_tmpl(name):
    with open(os.path.join(TMPL_DIR, name), "r") as f:
        return f.read()


DIR_TMPL = load_tmpl("dir.html")
MD_TMPL = load_tmpl("md.html")
CODE_TMPL = load_tmpl("code.html")
TOOLBAR_TMPL = load_tmpl("toolbar.html")
CSV_TMPL = load_tmpl("csv.html")
VIDEO_TMPL = load_tmpl("video.html")


# File extensions rendered with the code.html template (highlight.js + Ace)
# Matching: first by extension, then by full filename for extensionless files
TEXT_EXTENSIONS = {
    ".txt", ".csv", ".log", ".py", ".sh", ".bash", ".zsh", ".rb", ".go", ".rs",
    ".js", ".jsx", ".ts", ".tsx", ".c", ".h", ".cpp", ".hpp", ".cc",
    ".java", ".kt", ".scala", ".swift", ".r", ".m", ".mm",
    ".yaml", ".yml", ".toml", ".json", ".xml", ".sql",
    ".css", ".scss", ".less", ".php", ".pl", ".lua", ".dart",
    ".lisp", ".clj", ".hs", ".ex", ".exs", ".erl",
    ".cfg", ".ini", ".conf", ".env", ".vue", ".svelte",
    ".tex", ".vim", ".dockerfile", ".makefile", ".gradle",
    # Dotfiles and extensionless files
    ".gitignore", ".dockerignore", ".editorconfig", ".gitattributes",
    ".gitmodules", ".env.example", ".python-version", ".nvmrc",
    "dockerfile", "makefile",
}

# Extension → highlight.js language mapping
LANG_MAP = {
    ".py": "python",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".txt": "plaintext",
    ".csv": "plaintext",
    ".log": "plaintext",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp",
    ".java": "java",
    ".kt": "kotlin",
    ".scala": "scala",
    ".swift": "swift",
    ".r": "r",
    ".m": "objectivec", ".mm": "objectivec",
    ".yaml": "yaml", ".yml": "yaml",
    ".toml": "ini",
    ".json": "json",
    ".xml": "xml",
    ".sql": "sql",
    ".css": "css", ".scss": "scss", ".less": "less",
    ".php": "php",
    ".pl": "perl",
    ".lua": "lua",
    ".dart": "dart",
    ".lisp": "lisp",
    ".clj": "clojure",
    ".hs": "haskell",
    ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang",
    ".cfg": "ini", ".ini": "ini", ".conf": "ini", ".env": "ini",
    ".vue": "html",
    ".svelte": "html",
    ".dockerfile": "dockerfile",
    ".tex": "latex",
    ".vim": "vim",
    # Dotfiles and extensionless files
    ".gitignore": "plaintext",
    ".dockerignore": "plaintext",
    ".editorconfig": "ini",
    ".gitattributes": "plaintext",
    ".gitmodules": "ini",
    ".env.example": "ini",
    ".python-version": "plaintext",
    ".nvmrc": "plaintext",
    "dockerfile": "dockerfile",
    "makefile": "makefile",
}

# Mapeo de lenguaje highlight.js a modo Ace editor
ACE_MODE_MAP = {
    "python": "python",
    "bash": "sh",
    "ruby": "ruby",
    "go": "golang",
    "rust": "rust",
    "javascript": "javascript",
    "typescript": "typescript",
    "c": "c_cpp",
    "cpp": "c_cpp",
    "java": "java",
    "kotlin": "kotlin",
    "scala": "scala",
    "swift": "swift",
    "r": "r",
    "objectivec": "c_cpp",
    "yaml": "yaml",
    "toml": "ini",
    "json": "json",
    "xml": "xml",
    "sql": "sql",
    "css": "css",
    "scss": "scss",
    "less": "less",
    "php": "php",
    "perl": "perl",
    "lua": "lua",
    "dart": "dart",
    "lisp": "lisp",
    "clojure": "clojure",
    "haskell": "haskell",
    "elixir": "elixir",
    "erlang": "erlang",
    "html": "html",
    "dockerfile": "dockerfile",
    "latex": "latex",
    "vim": "text",
    "ini": "ini",
    "plaintext": "text",
    "makefile": "text",
}


def render_md(text, path, full):
    title = "Documento"
    m = re.search(r"^# (.+)", text, re.MULTILINE)
    if m:
        title = m.group(1)
    bc = breadcrumb_code(path, full)
    toolbar = TOOLBAR_TMPL.replace("{{breadcrumb}}", bc).replace("{{root_name}}", ROOT_NAME)
    safe_json = json.dumps(text).replace("</", "<\\/")
    return MD_TMPL.replace("{{title}}", title)\
        .replace("{{toolbar_html}}", toolbar)\
        .replace("{{json_content}}", safe_json)


def breadcrumb_code(path, full):
    """Breadcrumb with clickable segments that open a directory modal."""
    dir_path = os.path.dirname(path.rstrip("/")) or "/"
    current_file = os.path.basename(full) if os.path.isfile(full) else ""
    parent_full = os.path.dirname(full) if os.path.isfile(full) else full

    parts = dir_path.strip("/").split("/") if dir_path != "/" else []
    accum = ""
    items = [f'<span class="bc-link" data-dir="/">{ROOT_NAME}</span>']
    for part in parts:
        accum += "/" + part
        items.append(f'<span class="bc-link" data-dir="{accum}/">{part}</span>')

    sep = '<span class="bc-sep"> / </span>'
    bc = sep.join(items)

    if current_file:
        bc += sep + f'<span class="bc-current">{current_file}</span>'

    return bc


def render_code(text, text_key, path, full):
    lang = LANG_MAP.get(text_key, "plaintext")
    ace_lang = ACE_MODE_MAP.get(lang, "text")
    bc = breadcrumb_code(path, full)
    toolbar = TOOLBAR_TMPL.replace("{{breadcrumb}}", bc).replace("{{root_name}}", ROOT_NAME)
    safe_content = json.dumps(text).replace("</", "<\\/")
    safe_lang = json.dumps(lang).replace("</", "<\\/")
    safe_ace = json.dumps(ace_lang).replace("</", "<\\/")
    return CODE_TMPL.replace("{{title}}", os.path.basename(full))\
        .replace("{{toolbar_html}}", toolbar)\
        .replace("{{language}}", "language-" + lang)\
        .replace("{{json_language}}", safe_lang)\
        .replace("{{json_ace_lang}}", safe_ace)\
        .replace("{{json_content}}", safe_content)


def render_csv(path, full):
    title = os.path.basename(full)
    bc = breadcrumb_code(path, full)
    toolbar = TOOLBAR_TMPL.replace("{{breadcrumb}}", bc).replace("{{root_name}}", ROOT_NAME)
    return CSV_TMPL.replace("{{title}}", title)\
        .replace("{{toolbar_html}}", toolbar)


def breadcrumb_html(path):
    if path == "/":
        return f'<span class="bc-link" data-dir="/">{ROOT_NAME}</span>'
    parts = path.strip("/").split("/")
    accum = ""
    items = [f'<span class="bc-link" data-dir="/">{ROOT_NAME}</span>']
    for part in parts:
        accum += "/" + part
        items.append(f'<span class="bc-link" data-dir="{accum}/">{part}</span>')
    sep = '<span class="bc-sep"> / </span>'
    return sep.join(items)


def format_size(s):
    for unit in ["B", "KB", "MB", "GB"]:
        if s < 1024:
            return f"{s:.1f} {unit}"
        s /= 1024
    return f"{s:.1f} TB"


def format_date(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")




def list_dir(full, sort, order):
    entries = []
    for entry in os.scandir(full):
        st = entry.stat()
        entries.append(
            {
                "name": entry.name,
                "size": st.st_size if entry.is_file() else 0,
                "date": st.st_mtime,
                "is_dir": entry.is_dir(),
            }
        )

    rev = order == "desc"
    if sort == "name":
        entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()), reverse=rev)
    elif sort == "size":
        entries.sort(key=lambda e: (not e["is_dir"], e["size"]), reverse=rev)
    elif sort == "date":
        entries.sort(key=lambda e: (not e["is_dir"], e["date"]), reverse=rev)
    else:
        entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))

    return entries






class Handler(http.server.SimpleHTTPRequestHandler):
    root_dir = SCRIPT_DIR  # will be overridden after arg parse
    real_root = SCRIPT_DIR

    def _serve_file_range(self, full, mime):
        """Serve a file with Range request support for video seeking."""
        file_size = os.path.getsize(full)
        range_header = self.headers.get("Range")

        if range_header:
            # Parse Range: bytes=start-end
            m = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if m:
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else file_size - 1
                end = min(end, file_size - 1)
                length = end - start + 1

                self.send_response(206)
                self.send_header("Content-type", mime)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(full, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
                return

        # No Range header: serve full file
        self.send_response(200)
        self.send_header("Content-type", mime)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

        with open(full, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def do_HEAD(self):
        """Support HEAD requests for video preflight."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        full = os.path.abspath(os.path.join(self.root_dir, path.lstrip("/")))
        real = os.path.realpath(full)

        if not (real.startswith(self.real_root) or full.startswith(self.root_dir)):
            self.send_error(403)
            return

        if not os.path.isfile(full):
            self.send_error(404)
            return

        ext = os.path.splitext(full)[1].lower()
        video_exts = {".mp4": "video/mp4", ".webm": "video/webm", ".ogg": "video/ogg", ".mov": "video/quicktime", ".mkv": "video/x-matroska"}
        mime = video_exts.get(ext)
        if mime:
            file_size = os.path.getsize(full)
            self.send_response(200)
            self.send_header("Content-type", mime)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
        else:
            self.send_response(200)
            self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        sort = qs.get("sort", ["name"])[0]
        order = qs.get("order", ["asc"])[0]
        full = os.path.abspath(os.path.join(self.root_dir, path.lstrip("/")))
        real = os.path.realpath(full)

        # Allow if real path is within root, OR if the unresolved path
        # is within root (supports symlinks that point outside)
        if not (real.startswith(self.real_root) or full.startswith(self.root_dir)):
            self.send_error(403)
            return

        # Serve static files (filex's own JS, CSS, images)
        if path.startswith("/static/"):
            static_root = os.path.join(SCRIPT_DIR, "static")
            rel = path[len("/static/"):]
            safe = os.path.normpath(os.path.join(static_root, rel))
            if not safe.startswith(os.path.normpath(static_root)):
                self.send_error(403)
                return
            static_mime = {
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".png": "image/png",
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".svg": "image/svg+xml",
                ".ico": "image/x-icon",
                ".mp4": "video/mp4",
                ".webm": "video/webm",
                ".ogg": "video/ogg",
                ".mov": "video/quicktime",
                ".mp3": "audio/mpeg",
                ".wav": "audio/wav",
                ".pdf": "application/pdf",
                ".mkv": "video/x-matroska",
            }
            sext = os.path.splitext(safe)[1].lower()
            try:
                with open(safe, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-type", static_mime.get(sext, "application/octet-stream"))
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self.send_error(404, "Static file not found")
            return

        if os.path.isdir(full):
            if qs.get("format", [None])[0] == "json":
                try:
                    entries = list_dir(full, sort, order)
                    data = [{
                        "name": e["name"],
                        "is_dir": e["is_dir"],
                        "size": e["size"],
                        "size_fmt": format_size(e["size"]) if not e["is_dir"] else "",
                        "date": format_date(e["date"]),
                    } for e in entries]
                    self.send_response(200)
                    self.send_header("Content-type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode("utf-8"))
                except Exception as e:
                    self.send_error(500, str(e))
                return
            # Viewing a directory: show toolbar with create/upload buttons
            bc = breadcrumb_html(path.rstrip("/") or "/")
            toolbar = TOOLBAR_TMPL.replace("{{breadcrumb}}", bc).replace("{{root_name}}", ROOT_NAME)
            title = os.path.basename(path.rstrip("/")) if path != "/" else ROOT_NAME
            page = (
                '<!doctype html><html lang="es"><head>'
                '<meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" />'
                f'<title>{title}</title>'
                '<link rel="stylesheet" href="/static/style.css" />'
                '<script src="/static/filex.js"></script>'
                '</head><body>'
                + toolbar +
                '<p style="margin:24px;color:#999;font-size:14px">'
                '📂 Navega por los directorios desde el breadcrumb.</p>'
                '<script>showFileActions();</script>'
                '</body></html>'
            )
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page.encode("utf-8"))
            return

        ext = os.path.splitext(full)[1].lower()
        # For dotfiles (.gitignore, .env) and extensionless files (Makefile),
        # use the full filename as lookup key
        text_key = ext if ext else os.path.basename(full).lower()

        if ext == ".md":
            try:
                with open(full, "r") as f:
                    text = f.read()
                if qs.get("raw", [None])[0]:
                    self.send_response(200)
                    self.send_header("Content-type", "text/markdown; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(text.encode("utf-8"))
                    return
                page = render_md(text, path, full)
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page.encode("utf-8"))
            except Exception as e:
                self.send_error(500, str(e))
            return

        if ext == ".csv":
            fmt = qs.get("format", [None])[0]
            if fmt == "sql":
                query = qs.get("q", [None])[0]
                if not query:
                    self.send_error(400, "Missing 'q' parameter")
                    return
                try:
                    conn = duckdb.connect()
                    conn.execute(f"CREATE VIEW data AS SELECT * FROM read_csv_auto('{full}')")
                    page = qs.get("page", [None])[0]
                    size = qs.get("size", [None])[0]
                    if page and size:
                        page = int(page)
                        size = int(size)
                        total = conn.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]
                        paginated = f"SELECT * FROM ({query}) LIMIT {size} OFFSET {(page-1)*size}"
                        result = conn.execute(paginated)
                    else:
                        result = conn.execute(query)
                    columns = [desc[0] for desc in result.description]
                    rows = result.fetchall()
                    conn.close()
                    buf = io.StringIO()
                    csvw = csv.writer(buf)
                    csvw.writerow(columns)
                    csvw.writerows(rows)
                    csv_data = buf.getvalue()
                    self.send_response(200)
                    self.send_header("Content-type", "text/csv; charset=utf-8")
                    if page and size:
                        self.send_header("X-Total-Rows", str(total))
                    self.end_headers()
                    self.wfile.write(csv_data.encode("utf-8"))
                except Exception as e:
                    self.send_error(500, str(e))
                return
            try:
                page = render_csv(path, full)
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page.encode("utf-8"))
            except Exception as e:
                self.send_error(500, str(e))
            return

        # Code/text files → render with template + highlight.js
        if text_key in TEXT_EXTENSIONS:
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                if qs.get("raw", [None])[0]:
                    mime = "text/plain; charset=utf-8"
                    if text_key == ".json":
                        mime = "application/json; charset=utf-8"
                    elif text_key == ".csv":
                        mime = "text/csv; charset=utf-8"
                    self.send_response(200)
                    self.send_header("Content-type", mime)
                    self.end_headers()
                    self.wfile.write(text.encode("utf-8"))
                    return
                html_out = render_code(text, text_key, path, full)
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_out.encode("utf-8"))
            except FileNotFoundError:
                self.send_error(404, "File not found")
            except Exception as e:
                self.send_error(500, str(e))
            return

        # Image/audio/video MIME mapping
        img_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}
        audio_exts = {".mp3", ".wav", ".flac", ".opus"}
        video_exts = {".mp4": "video/mp4", ".webm": "video/webm", ".ogg": "video/ogg", ".mov": "video/quicktime", ".mkv": "video/x-matroska"}
        media_mime = {
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".gif": "image/gif", ".webp": "image/webp",
            ".svg": "image/svg+xml", ".ico": "image/x-icon",
            ".mp3": "audio/mpeg", ".wav": "audio/wav",
            ".flac": "audio/flac", ".opus": "audio/opus",
            **video_exts,
        }

        is_video = ext in video_exts
        is_image = ext in img_exts
        is_media = ext in media_mime and ext != ".html"

        # Media: serve HTML wrapper with toolbar (browser navigation), raw binary otherwise (img tags)
        accept = self.headers.get("Accept", "")
        wants_html = "text/html" in accept or not accept
        if is_media and wants_html and not qs.get("raw", [None])[0]:
            bc = breadcrumb_code(path, full)
            toolbar = TOOLBAR_TMPL.replace("{{breadcrumb}}", bc).replace("{{root_name}}", ROOT_NAME)
            sep = "&" if parsed.query else "?"
            media_src = self.path + sep + "raw=1"
            title = os.path.basename(full)
            if is_image:
                page = (
                    '<!doctype html><html lang="en"><head>'
                    '<meta charset="utf-8" />'
                    '<meta name="viewport" content="width=device-width,initial-scale=1" />'
                    f'<title>{html_mod.escape(title)}</title>'
                    '<link rel="stylesheet" href="/static/style.css" />'
                    '<script src="/static/filex.js"></script>'
                    '<style>.img-wrap{max-width:100%;margin:16px auto;text-align:center}'
                    '.img-wrap img{max-width:100%;height:auto;border-radius:4px;box-shadow:0 2px 12px rgba(0,0,0,0.15)}</style>'
                    '</head><body>'
                    f'{toolbar}'
                    f'<div class="img-wrap"><img src="{html_mod.escape(media_src)}" alt="{html_mod.escape(title)}" /></div>'
                    '</body></html>'
                )
            else:
                page = VIDEO_TMPL.replace("{{title}}", title).replace("{{toolbar_html}}", toolbar).replace("{{video_src}}", media_src)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page.encode("utf-8"))
            return

        # Media raw: serve binary with correct MIME type
        if is_media:
            try:
                if is_video:
                    self._serve_file_range(full, media_mime[ext])
                else:
                    with open(full, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-type", media_mime[ext])
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
            except FileNotFoundError:
                self.send_error(404, "File not found")
            except Exception as e:
                self.send_error(500, str(e))
            return

        # Fallback: abrir inline, descargar solo si ?dl=1
        if qs.get("dl", [None])[0]:
            try:
                with open(full, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(full)}"')
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self.send_error(404, "File not found")
            except Exception as e:
                self.send_error(500, str(e))
            return

        # Intentar abrir como texto
        try:
            file_size = os.path.getsize(full)
            MAX_INLINE = 10 * 1024 * 1024  # 10 MB
            if file_size > MAX_INLINE:
                page = (
                    '<!doctype html><html lang="es"><head>'
                    '<meta charset="utf-8" />'
                    f'<title>{html_mod.escape(os.path.basename(full))}</title>'
                    '<link rel="stylesheet" href="/static/style.css" />'
                    '</head><body>'
                    f'<p style="margin:24px;font-size:14px">'
                    f'Archivo demasiado grande ({format_size(file_size)}). '
                    f'<a href="{self.path}?dl=1">Descargar</a></p>'
                    '</body></html>'
                )
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page.encode("utf-8"))
                return
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            html_out = render_code(text, os.path.basename(full).lower(), path, full)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_out.encode("utf-8"))
        except FileNotFoundError:
            self.send_error(404, "File not found")
        except Exception:
            # Si falla como texto, servir binario con Content-Disposition inline
            try:
                with open(full, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-type", "application/octet-stream")
                self.send_header("Content-Disposition", "inline")
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self.send_error(404, "File not found")
            except Exception as e:
                self.send_error(500, str(e))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        full = os.path.abspath(os.path.join(self.root_dir, path.lstrip("/")))
        real = os.path.realpath(full)

        if not (real.startswith(self.real_root) or full.startswith(self.root_dir)):
            self.send_error(403)
            return

        if not os.path.isfile(full):
            self.send_error(404, "File not found")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            params = urllib.parse.parse_qs(body)
            content = params.get("content", [None])[0]
            if content is None:
                self.send_error(400, "Missing 'content' field")
                return
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_error(500, str(e))

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        full = os.path.abspath(os.path.join(self.root_dir, path.lstrip("/")))
        real = os.path.realpath(full)

        if not (real.startswith(self.real_root) or full.startswith(self.root_dir)):
            self.send_error(403)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            parent = os.path.dirname(full)
            os.makedirs(parent, exist_ok=True)

            exists = os.path.isfile(full)
            with open(full, "wb") as f:
                f.write(body)

            if exists:
                self.send_response(200)
            else:
                self.send_response(201)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_error(500, str(e))

    def do_MKCOL(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        full = os.path.abspath(os.path.join(self.root_dir, path.lstrip("/")))
        real = os.path.realpath(full)

        if not (real.startswith(self.real_root) or full.startswith(self.root_dir)):
            self.send_error(403)
            return

        if os.path.exists(full):
            self.send_error(405, "Directory already exists")
            return

        try:
            os.makedirs(full, exist_ok=False)
            self.send_response(201)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Created")
        except Exception as e:
            self.send_error(500, str(e))

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        full = os.path.abspath(os.path.join(self.root_dir, path.lstrip("/")))
        real = os.path.realpath(full)

        if not (real.startswith(self.real_root) or full.startswith(self.root_dir)):
            self.send_error(403)
            return

        if not os.path.exists(full):
            self.send_error(404, "Not found")
            return

        try:
            if os.path.isdir(full):
                import shutil
                shutil.rmtree(full)
            else:
                os.remove(full)
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Deleted")
        except Exception as e:
            self.send_error(500, str(e))

    def do_MOVE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        full = os.path.abspath(os.path.join(self.root_dir, path.lstrip("/")))
        real = os.path.realpath(full)

        if not (real.startswith(self.real_root) or full.startswith(self.root_dir)):
            self.send_error(403)
            return

        if not os.path.exists(full):
            self.send_error(404, "Not found")
            return

        dest = self.headers.get("Destination")
        if not dest:
            self.send_error(400, "Missing Destination header")
            return

        dest_parsed = urllib.parse.urlparse(dest)
        dest_path = dest_parsed.path
        dest_full = os.path.abspath(os.path.join(self.root_dir, dest_path.lstrip("/")))
        dest_real = os.path.realpath(dest_full)

        if not (dest_real.startswith(self.real_root) or dest_full.startswith(self.root_dir)):
            self.send_error(403, "Destination outside root")
            return

        try:
            dest_parent = os.path.dirname(dest_full)
            os.makedirs(dest_parent, exist_ok=True)
            os.rename(full, dest_full)
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Moved")
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, fmt, *args):
        pass


def install_service():
    """Install filex as a systemd --user service."""
    import shutil
    service_dir = os.path.expanduser("~/.local/bin")
    os.makedirs(service_dir, exist_ok=True)
    dst = os.path.join(service_dir, "filex")
    src = os.path.abspath(sys.argv[0])
    shutil.copy2(src, dst)
    print(f"Installed binary to {dst}")

    service_path = os.path.expanduser("~/.config/systemd/user/filex.service")
    os.makedirs(os.path.dirname(service_path), exist_ok=True)
    content = f"""[Unit]
Description=FileX — file server with Markdown rendering
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/filex --root %h --port 9090 --bind 0.0.0.0
Restart=always
RestartSec=5
WorkingDirectory=%h
Environment=FILEX_BIN=%h/.local/bin/filex

[Install]
WantedBy=default.target
"""
    with open(service_path, "w") as f:
        f.write(content)
    print(f"Service file written to {service_path}")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "enable", "--now", "filex"], check=False)
    print("Service started. Open http://localhost:9090")


def uninstall_service():
    """Stop and remove the systemd service."""
    service_path = os.path.expanduser("~/.config/systemd/user/filex.service")
    subprocess.run(["systemctl", "--user", "stop", "filex"], check=False)
    subprocess.run(["systemctl", "--user", "disable", "filex"], check=False)
    if os.path.exists(service_path):
        os.remove(service_path)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    bin_path = os.path.expanduser("~/.local/bin/filex")
    if os.path.exists(bin_path):
        os.remove(bin_path)
        print(f"Removed {bin_path}")
    print("Service removed.")


def uninstall_service():
    """Stop and remove the systemd service."""
    service_path = os.path.expanduser("~/.config/systemd/user/filex.service")
    subprocess.run(["systemctl", "--user", "stop", "filex"], check=False)
    subprocess.run(["systemctl", "--user", "disable", "filex"], check=False)
    if os.path.exists(service_path):
        os.remove(service_path)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    print("Service removed.")


if __name__ == "__main__":
    import sys
    import subprocess
    import argparse
    parser = argparse.ArgumentParser(description="File server with Markdown rendering")
    parser.add_argument("--root", default=os.getcwd(), help="Root directory to serve (default: current dir)")
    parser.add_argument("--port", type=int, default=9090, help="Port to listen on")
    parser.add_argument("--bind", default="0.0.0.0", help="Address to bind")
    parser.add_argument("--install", action="store_true", help="Install as systemd --user service")
    parser.add_argument("--uninstall", action="store_true", help="Remove systemd service")
    args = parser.parse_args()

    if args.install:
        install_service()
        sys.exit(0)
    if args.uninstall:
        uninstall_service()
        sys.exit(0)

    Handler.root_dir = os.path.abspath(args.root)
    Handler.real_root = os.path.realpath(Handler.root_dir)
    ROOT_NAME = os.path.basename(Handler.root_dir)
    print(f"Serving {Handler.root_dir} at http://{args.bind}:{args.port}")
    server = http.server.HTTPServer((args.bind, args.port), Handler)
    server.serve_forever()
