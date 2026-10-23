#!/usr/bin/env bash
# Add "ORFS Flow Runner" to the desktop's application menu (and the Desktop folder, if there is one).
# Usage: gui/install_launcher.sh [--uninstall]
set -euo pipefail

APP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/orfs_app.py"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
NAME=orfs-flow-runner.desktop

if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$APPS/$NAME" "$DESKTOP_DIR/$NAME"
  echo "removed $APPS/$NAME"
  exit 0
fi

mkdir -p "$APPS"
# The menu entry starts with a minimal PATH, so record where the tools are now.
cat > "$APPS/$NAME" <<EOF
[Desktop Entry]
Type=Application
Name=ORFS Flow Runner
Comment=Run OpenROAD-flow-scripts designs from RTL to GDS
Exec=env PATH=$PATH python3 "$APP"
Icon=applications-engineering
Terminal=false
Categories=Development;Electronics;
EOF
chmod +x "$APPS/$NAME"
echo "installed $APPS/$NAME"

if [ -d "$DESKTOP_DIR" ]; then
  cp "$APPS/$NAME" "$DESKTOP_DIR/$NAME"
  gio set "$DESKTOP_DIR/$NAME" metadata::trusted true 2>/dev/null || true
  echo "copied to $DESKTOP_DIR (right-click it and choose \"Allow Launching\" if GNOME asks)"
fi
