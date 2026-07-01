#!/usr/bin/env bash
# Regenerate filex UI screenshots for README.
# Requires: agent-browser, Chrome running with CDP on port 9222, filex server on :9090
set -euo pipefail
OUT="${1:-../screenshots}"
mkdir -p "$OUT"

echo "=== Screenshot 1: Directory listing ==="
agent-browser --cdp 9222 set viewport 608 1080
agent-browser --cdp 9222 open "http://localhost:9090/code"
sleep 2
agent-browser --cdp 9222 screenshot "$OUT/dir-listing.png"

echo "=== Screenshot 2: Code viewer ==="
agent-browser --cdp 9222 open "http://localhost:9090/code/filex/serve_md.py"
sleep 2
agent-browser --cdp 9222 screenshot "$OUT/code-viewer.png"

echo "=== Screenshot 3: Markdown renderer ==="
agent-browser --cdp 9222 open "http://localhost:9090/code/filex/README.md"
sleep 2
agent-browser --cdp 9222 screenshot "$OUT/markdown-viewer.png"

echo "=== Done ==="
ls -la "$OUT/"*.png
