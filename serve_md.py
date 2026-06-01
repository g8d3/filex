#!/usr/bin/env python3
"""Explorador de archivos con columnas ordenables. Renderiza .md como HTML."""

import http.server
import os
import re
import urllib.parse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMPL_DIR = os.path.join(SCRIPT_DIR, "templates")


def load_tmpl(name):
    with open(os.path.join(TMPL_DIR, name), "r") as f:
        return f.read()


DIR_TMPL = load_tmpl("dir.html")
MD_TMPL = load_tmpl("md.html")


def render_md(text, parent_path="/"):
    lines = text.split("\n")
    in_code = False
    in_table = False
    in_list = False
    result = []

    for line in lines:
        if line.startswith("```"):
            if in_code:
                result.append("</code></pre>")
                in_code = False
            else:
                result.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            result.append(line)
            continue

        if line.startswith("# "):
            result.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            result.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            result.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if all(re.match(r"^-+$", c) for c in cells):
                continue
            if not in_table:
                result.append("<table><tr>")
                in_table = True
            else:
                result.append("</tr><tr>")
            for c in cells:
                result.append(f"<td>{c}</td>")
        else:
            if in_table:
                result.append("</tr></table>")
                in_table = False
            if line.startswith("- "):
                if not in_list:
                    result.append("<ul>")
                    in_list = True
                result.append(f"<li>{line[2:]}</li>")
            else:
                if in_list:
                    result.append("</ul>")
                    in_list = False
                if line.strip():
                    processed = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
                    result.append(f"<p>{processed}</p>")
                else:
                    result.append("<br>")

    if in_table:
        result.append("</tr></table>")
    if in_list:
        result.append("</ul>")
    if in_code:
        result.append("</code></pre>")

    body = "\n".join(result)
    title = "Documento"
    m = re.search(r"<h1>(.+?)</h1>", body)
    if m:
        title = m.group(1)
    return MD_TMPL.replace("{{title}}", title).replace("{{content}}", body).replace("{{parent_path}}", parent_path)


def breadcrumb_html(path):
    if path == "/":
        return '<span class="bc-root">/</span>'
    parts = path.strip("/").split("/")
    accum = ""
    items = ['<a href="/" class="bc-link">/</a>']
    for i, part in enumerate(parts):
        accum += "/" + part
        if i < len(parts) - 1:
            items.append(f'<a href="{accum}/" class="bc-link">{part}</a>')
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

        if os.path.isdir(full):
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
                html = render_md(text, os.path.dirname(path.rstrip("/")) or "/")
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            except Exception as e:
                self.send_error(500, str(e))
            return

        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".txt": "text/plain; charset=utf-8",
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
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

        # Fallback: serve any other file type
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
    print(f"Sirviendo {Handler.root_dir} en http://{args.bind}:{args.port}")
    server = http.server.HTTPServer((args.bind, args.port), Handler)
    server.serve_forever()
