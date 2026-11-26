#!/usr/bin/env bash
# FABP – Free All Bluetooth Printers: Linux installer (no root needed, except for tkinter)
set -e
DIR="$HOME/.local/share/fabp"
SRC="$(cd "$(dirname "$0")" && pwd)"

command -v python3 >/dev/null || { echo "Please install python3 first."; exit 1; }
if ! python3 -c "import tkinter" 2>/dev/null; then
  echo "tkinter is missing (needed for the window). Install it with one of:"
  echo "  sudo apt install python3-tk python3-venv   (Debian/Ubuntu/Mint)"
  echo "  sudo dnf install python3-tkinter          (Fedora)"
  echo "  sudo pacman -S tk                         (Arch)"
  echo "The command-line version will still work."
fi

mkdir -p "$DIR" "$HOME/.local/bin" "$HOME/.local/share/applications"
python3 -m venv "$DIR/venv"
"$DIR/venv/bin/pip" install -q --upgrade pip
"$DIR/venv/bin/pip" install -q bleak pillow
cp "$SRC/fabp.py" "$DIR/fabp.py"

cat > "$HOME/.local/bin/fabp" <<EOF
#!/usr/bin/env bash
exec "$DIR/venv/bin/python" "$DIR/fabp.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/fabp"

cat > "$HOME/.local/share/applications/fabp.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=FABP
Comment=Free All Bluetooth Printers
Exec=$HOME/.local/bin/fabp
Icon=printer
Terminal=false
Categories=Graphics;Utility;
EOF

echo
echo "Done! Start FABP from your app menu, or run:  fabp"
echo "(If 'fabp' is not found, log out and in again, or use: ~/.local/bin/fabp)"
