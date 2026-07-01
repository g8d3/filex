#!/usr/bin/env bash
set -euo pipefail
REPO=${REPO:-g8d3/filex}
BRANCH=${BRANCH:-main}
DIR="${DIR:-$HOME/code/filex}"

echo "==> Cloning filex..."
git clone --depth=1 "https://github.com/$REPO.git" "$DIR"

echo "==> Setting up virtualenv..."
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install duckdb -q

if [[ "${1:-}" == "--service" ]]; then
    echo "==> Installing systemd service..."
    mkdir -p "$HOME/.config/systemd/user"
    cp "$DIR/filex.service" "$HOME/.config/systemd/user/"
    systemctl --user daemon-reload
    systemctl --user enable --now filex
    echo "==> Service installed and started."
else
    echo "==> Done."
fi

echo ""
echo "  Serve:  $DIR/.venv/bin/python3 $DIR/serve_md.py --root /your/dir"
echo "  Service:  $DIR/scripts/install.sh --service"
echo "  Open:  http://localhost:9090"
