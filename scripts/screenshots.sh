#!/usr/bin/env bash
# Regenerate filex UI screenshots for README.
# Requires: agent-browser, Chrome running with CDP on port 9222, filex server on :9090
set -euo pipefail
OUT="${1:-../screenshots}"
mkdir -p "$OUT"
CDP="${CDP:-9222}"
FONT_CLICKS="${FONT_CLICKS:-3}"

screenshot() {
  local label="$1" url="$2" file="$3"
  echo "=== $label ==="
  agent-browser --cdp "$CDP" open "$url"
  sleep 2
  for _ in $(seq 1 "$FONT_CLICKS"); do
    agent-browser --cdp "$CDP" click "A+" 2>/dev/null || true
    sleep 0.5
  done
  agent-browser --cdp "$CDP" screenshot "$OUT/$file"
}

echo "=== Setting viewport ==="
agent-browser --cdp "$CDP" set viewport 608 1080

screenshot "Screenshot 1: Directory listing" \
  "http://localhost:9090/code" \
  "dir-listing.png"

screenshot "Screenshot 2: CSV viewer" \
  "http://localhost:9090/code/web9-agent/old/low_code_repositories.csv" \
  "csv-viewer.png"

screenshot "Screenshot 3: Code viewer" \
  "http://localhost:9090/code/filex/serve_md.py" \
  "code-viewer.png"

screenshot "Screenshot 4: Markdown renderer" \
  "http://localhost:9090/code/filex/README.md" \
  "markdown-viewer.png"

echo "=== Adding border to screenshots ==="
for f in "$OUT"/*.png; do
  convert "$f" -bordercolor "#ddd" -border 1x1 "$f"
done

echo "=== Done ==="
ls -la "$OUT/"*.png
