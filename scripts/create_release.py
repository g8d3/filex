#!/usr/bin/env python3
"""Fill the GitHub release form via CDP and upload the binary."""
import json, urllib.request, time
from websockets.sync.client import connect

data = json.loads(urllib.request.urlopen("http://localhost:9222/json").read())
page = [d for d in data if d["type"] == "page"][0]

desc_text = """First public release of **filex** — mobile-first file server with Markdown rendering, code viewer/editor, CSV tables, and video streaming.

## Features
- **Directory browser** — sortable columns, breadcrumb navigation
- **Markdown renderer** — rendered client-side with marked.js
- **Code viewer** — syntax highlighting (highlight.js) + Ace editor
- **CSV viewer** — sortable, paginated tables via PapaParse
- **Video/audio streaming** — Range request support
- **File operations** — create dirs, upload files, rename, delete
- **Mobile-first** — bottom toolbar, responsive layout

## Install
```
bash <(curl -fsSL https://raw.githubusercontent.com/g8d3/filex/main/scripts/install.sh)
```"""

with connect(page["webSocketDebuggerUrl"]) as ws:
    cmd = json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {
        "expression": """
        (() => {
            const ta = document.querySelector('textarea[name="release[body]"]');
            if (!ta) return 'no textarea';
            ta.value = arguments[0];
            ta.dispatchEvent(new Event('input', { bubbles: true }));
            return 'filled: ' + ta.value.length + ' chars';
        })()
        """,
        "arguments": [{"value": desc_text}]
    }})
    ws.send(cmd)
    time.sleep(2)
    resp = json.loads(ws.recv(timeout=5))
    print("Result:", resp.get("result", {}).get("result", {}).get("value", "N/A"))
