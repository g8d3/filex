# filex

**Mobile-first file server** with Markdown rendering, code viewer/editor, CSV tables, and video streaming.

Serve any directory as a browsable, interactive web app — no framework, no database, just Python.

## Features

- **Directory browser** — sortable columns (name, size, date), sticky breadcrumb navigation
- **Markdown renderer** — headings, tables, code blocks, lists, images — rendered client-side with `marked.js`
- **Code viewer** — syntax highlighting for 40+ languages (`highlight.js`) + inline editor (`Ace`)
- **CSV viewer** — sortable, paginated HTML tables via `PapaParse`
- **Video/audio streaming** — Range request support for seeking in MP4, WebM, MP3, etc.
- **Mobile-first** — bottom toolbar, responsive layout, touch-friendly modal navigation
- **File operations** — create dirs, upload files, rename, delete (via GUI + API)
- **Editable** — save changes to any text file directly from the browser

## Quick start

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/g8d3/filex/main/scripts/install.sh)
```

Then open `http://localhost:9090`.

To serve a different directory:
```bash
~/.venv/bin/python3 ~/code/filex/serve_md.py --root /your/path
```

## Install as a service

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/g8d3/filex/main/scripts/install.sh) --service
```

Or manually:
```bash
cp ~/code/filex/filex.service ~/.config/systemd/user/ && systemctl --user daemon-reload && systemctl --user enable --now filex
```

Edit `filex.service` to change `--root`, `--port`, or `--bind`.

## Usage

| Flag | Default | Description |
|------|---------|-------------|
| `--root` | script directory | Root directory to serve |
| `--port` | 9090 | HTTP port |
| `--bind` | 0.0.0.0 | Interface to bind |

## Tech

- Pure Python (`http.server`), no frameworks
- `highlight.js` for code syntax
- `Ace Editor` for inline editing
- `marked.js` for Markdown rendering
- `PapaParse` for CSV parsing
- `duckdb` for CSV SQL queries

## License

MIT
