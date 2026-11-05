#!/bin/bash
# Golden Gate step one — appearance layer only.
# Writes only inside $HOME and the user's preferences domain.
# Does NOT touch the kernel, SIP, the sealed system volume, or any signed Apple content.
# Undo with restore-tahoe.sh.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
STATE="$HOME/.goldengate"
BKP="$STATE/backup"
mkdir -p "$BKP" "$HOME/Pictures"

echo "== Golden Gate step one =="

# ---- backup what we change ----
[ -f "$HOME/Library/Preferences/com.apple.desktop.plist" ] && \
  cp "$HOME/Library/Preferences/com.apple.desktop.plist" "$BKP/com.apple.desktop.plist" 2>/dev/null
defaults read -g AppleAccentColor      > "$BKP/AppleAccentColor.txt"      2>/dev/null || echo unset > "$BKP/AppleAccentColor.txt"
defaults read -g AppleHighlightColor   > "$BKP/AppleHighlightColor.txt"   2>/dev/null || echo unset > "$BKP/AppleHighlightColor.txt"
defaults read -g AppleInterfaceStyle   > "$BKP/AppleInterfaceStyle.txt"   2>/dev/null || echo Light > "$BKP/AppleInterfaceStyle.txt"
defaults read com.apple.dock tilesize  > "$BKP/dock-tilesize.txt"         2>/dev/null || echo 64 > "$BKP/dock-tilesize.txt"
defaults read com.apple.dock magnification > "$BKP/dock-magnification.txt" 2>/dev/null || echo 0 > "$BKP/dock-magnification.txt"
echo "backups: $BKP"

# ---- 1. wallpaper ----
WALL="$HOME/Pictures/GoldenGate.jpg"
cp "$HERE/GoldenGate.jpg" "$WALL"
# Set via the desktop preference domain: no Automation permission prompt, no System Events.
/usr/bin/python3 - "$WALL" <<'PY'
import plistlib, subprocess, sys, os
wall = sys.argv[1]
p = os.path.expanduser("~/Library/Preferences/com.apple.desktop.plist")
cur = {}
try:
    with open(p, "rb") as f: cur = plistlib.load(f)
except Exception: pass
bg = cur.get("Background") or {}
entry = {"Change": "never", "ChangePath": wall, "ChangeTime": 0,
         "DrawBackgroundColor": True, "ImageFile": wall, "ImageFileAlias": b"",
         "ImageFileEncrypted": False, "ImageFileURL": "file://" + wall.replace(" ", "%20"),
         "Placement": "FillScreen", "Random": False}
bg["default"] = entry
bg["Space"] = bg.get("Space") or {}
cur["Background"] = bg
with open(p, "wb") as f: plistlib.dump(cur, f)
print("wallpaper entry written")
PY
killall Dock 2>/dev/null
echo "wallpaper: $WALL"

# ---- 2. accent, highlight, dark mode ----
defaults write -g AppleAccentColor -int 3
defaults write -g AppleHighlightColor -string "0.980392 0.807843 0.294118"
defaults write -g AppleInterfaceStyleSwitchesAutomatically -bool false
defaults write -g AppleInterfaceStyle -string Dark
echo "accent gold, highlight gold, dark mode on"

# ---- 3. dock polish ----
defaults write com.apple.dock tilesize -int 48
defaults write com.apple.dock magnification -bool true
defaults write com.apple.dock largesize -int 72
killall Dock 2>/dev/null
echo "dock set"

# ---- 4. Golden Gate about panel ----
cat > "$STATE/about.sh" <<'ABOUT'
#!/bin/bash
osascript <<'AS'
tell application "System Events"
  display dialog "Golden Gate — step one

Built on the Tahoe kernel, which is unmodified.
macOS 27.2 userspace: not yet running.
This panel reports the project name, not the actual OS version.

Real version: 26.7.2 (25G332)" buttons {"OK"} default button 1 with title "About This Mac" with icon note
end tell
AS
ABOUT
chmod +x "$STATE/about.sh"
alias_line='alias about-gg="$HOME/.goldengate/about.sh"'
grep -qF "$alias_line" "$HOME/.zshrc" 2>/dev/null || echo "$alias_line" >> "$HOME/.zshrc"
echo "about panel: run  about-gg"

echo
echo "== done =="
echo "Undo:  bash $HERE/restore-tahoe.sh"
