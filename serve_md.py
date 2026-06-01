#!/usr/bin/env python3
"""Explorador de archivos con columnas ordenables. Renderiza .md como HTML."""

import http.server
import os
import re
import html
import json
import urllib.parse
from datetime import datetime

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


# Extensiones de archivos de código/texto que se renderizan con el template code.html
TEXT_EXTENSIONS = {
    ".txt", ".py", ".sh", ".bash", ".zsh", ".rb", ".go", ".rs",
    ".js", ".jsx", ".ts", ".tsx", ".c", ".h", ".cpp", ".hpp", ".cc",
    ".java", ".kt", ".scala", ".swift", ".r", ".m", ".mm",
    ".yaml", ".yml", ".toml", ".json", ".xml", ".sql",
    ".css", ".scss", ".less", ".php", ".pl", ".lua", ".dart",
    ".lisp", ".clj", ".hs", ".ex", ".exs", ".erl",
    ".cfg", ".ini", ".conf", ".env", ".vue", ".svelte",
    ".tex", ".vim", ".dockerfile", ".makefile", ".gradle",
}

# Mapeo de extensión a lenguaje highlight.js
LANG_MAP = {
    ".py": "python",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".txt": "plaintext",
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
}


def render_md(text, path, full):
    title = "Documento"
    m = re.search(r"^# (.+)", text, re.MULTILINE)
    if m:
        title = m.group(1)
    bc = breadcrumb_code(path, full)
    toolbar = TOOLBAR_TMPL.replace("{{breadcrumb}}", bc)
    return MD_TMPL.replace("{{title}}", title)\
        .replace("{{toolbar_html}}", toolbar)\
        .replace("{{json_content}}", json.dumps(text))


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


def render_code(text, ext, path, full):
    lang = LANG_MAP.get(ext, "plaintext")
    ace_lang = ACE_MODE_MAP.get(lang, "text")
    bc = breadcrumb_code(path, full)
    toolbar = TOOLBAR_TMPL.replace("{{breadcrumb}}", bc)
    return CODE_TMPL.replace("{{title}}", os.path.basename(full))\
        .replace("{{toolbar_html}}", toolbar)\
        .replace("{{language}}", lang)\
        .replace("{{json_content}}", json.dumps(text))\
        .replace("{{json_language}}", json.dumps(lang))\
        .replace("{{json_ace_lang}}", json.dumps(ace_lang))


def breadcrumb_html(path):
    if path == "/":
        return f'<span class="bc-link" data-dir="/">{ROOT_NAME}</span>'
    parts = path.strip("/").split("/")
    accum = ""
    items = [f'<span class="bc-link" data-dir="/">{ROOT_NAME}</span>']
    for i, part in enumerate(parts):
        accum += "/" + part
        if i < len(parts) - 1:
            items.append(f'<span class="bc-link" data-dir="{accum}/">{part}</span>')
        else:
            items.append(f'<span class="bc-current">{part}</span>')
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
    for name in os.listdir(full):
        fp = os.path.join(full, name)
        st = os.stat(fp)
        entries.append(
            {
                "name": name,
                "size": st.st_size if os.path.isfile(fp) else 0,
                "date": st.st_mtime,
                "is_dir": os.path.isdir(fp),
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


def render_dir(path, full, sort, order):
    entries = list_dir(full, sort, order)

    rows = ""
    for e in entries:
        link = (path + "/" + e["name"]).replace("//", "/")
        if e["is_dir"]:
            link += "/"
            rows += f'<tr><td class="name dir"><a href="{link}">{e["name"]}/</a></td>'
        else:
            rows += f'<tr><td class="name"><a href="{link}">{e["name"]}</a></td>'
        rows += (
            f'<td class="size">{format_size(e["size"]) if not e["is_dir"] else ""}</td>'
        )
        rows += f'<td class="date">{format_date(e["date"])}</td></tr>'

    def icon(s):
        return (
            " &#9660;"
            if s == sort and order == "desc"
            else " &#9650;" if s == sort else ""
        )

    def nxt(s):
        return "desc" if s == sort and order == "asc" else "asc"

    parent = os.path.dirname(path.rstrip("/"))
    if parent == path.rstrip("/"):
        parent = "/"
    parent_label = "Raiz" if parent == "/" else os.path.basename(parent)

    html = DIR_TMPL
    html = html.replace("{{parent}}", parent)
    html = html.replace("{{parent_label}}", parent_label)
    html = html.replace("{{breadcrumb}}", breadcrumb_html(path))
    html = html.replace("{{name_order}}", nxt("name"))
    html = html.replace("{{size_order}}", nxt("size"))
    html = html.replace("{{date_order}}", nxt("date"))
    html = html.replace("{{name_icon}}", icon("name"))
    html = html.replace("{{size_icon}}", icon("size"))
    html = html.replace("{{date_icon}}", icon("date"))
    html = html.replace("{{rows}}", rows)
    return html


class Handler(http.server.SimpleHTTPRequestHandler):
    root_dir = SCRIPT_DIR  # will be overridden after arg parse
    real_root = SCRIPT_DIR

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

        # Servir archivos estáticos (JS, CSS, imágenes del propio filex)
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
            html = render_dir(path.rstrip("/") or "/", full, sort, order)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        ext = os.path.splitext(full)[1].lower()
        if ext == ".md":
            try:
                with open(full, "r") as f:
                    text = f.read()
                html = render_md(text, path, full)
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            except Exception as e:
                self.send_error(500, str(e))
            return

        # Archivos de código/texto → render con template + highlight.js
        if ext in TEXT_EXTENSIONS:
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                html_out = render_code(text, ext, path, full)
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_out.encode("utf-8"))
            except FileNotFoundError:
                self.send_error(404, "File not found")
            except Exception as e:
                self.send_error(500, str(e))
            return

        # Archivos multimedia → servir binario
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".html": "text/html; charset=utf-8",
            ".pdf": "application/pdf",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }

        mime = mime_map.get(ext)
        if mime is not None:
            try:
                with open(full, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-type", mime)
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self.send_error(404, "File not found")
            except Exception as e:
                self.send_error(500, str(e))
            return

        # Fallback: cualquier otro archivo como descarga
        try:
            with open(full, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-type", "application/octet-stream")
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

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="File server with Markdown rendering")
    parser.add_argument("--root", default=SCRIPT_DIR, help=f"Root directory to serve")
    parser.add_argument("--port", type=int, default=9090, help="Port to listen on")
    parser.add_argument("--bind", default="0.0.0.0", help="Address to bind")
    args = parser.parse_args()
    Handler.root_dir = os.path.abspath(args.root)
    Handler.real_root = os.path.realpath(Handler.root_dir)
    ROOT_NAME = os.path.basename(Handler.root_dir)
    print(f"Sirviendo {Handler.root_dir} en http://{args.bind}:{args.port}")
    server = http.server.HTTPServer((args.bind, args.port), Handler)
    server.serve_forever()
