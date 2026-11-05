#!/bin/bash
# Undo apply-golden-gate.sh. Touches only $HOME and the user preference domain.
set -uo pipefail
BKP="$HOME/.goldengate/backup"

if [ -f "$BKP/com.apple.desktop.plist" ]; then
  cp "$BKP/com.apple.desktop.plist" "$HOME/Library/Preferences/com.apple.desktop.plist"
else
  rm -f "$HOME/Library/Preferences/com.apple.desktop.plist"
fi

v=$(cat "$BKP/AppleAccentColor.txt" 2>/dev/null || echo unset)
if [ "$v" = "unset" ]; then defaults delete -g AppleAccentColor 2>/dev/null; else defaults write -g AppleAccentColor -int "$v"; fi
v=$(cat "$BKP/AppleHighlightColor.txt" 2>/dev/null || echo unset)
if [ "$v" = "unset" ]; then defaults delete -g AppleHighlightColor 2>/dev/null; else defaults write -g AppleHighlightColor -string "$v"; fi
v=$(cat "$BKP/AppleInterfaceStyle.txt" 2>/dev/null || echo Light)
if [ "$v" = "Dark" ]; then defaults write -g AppleInterfaceStyle -string Dark; else defaults delete -g AppleInterfaceStyle 2>/dev/null; fi
defaults delete -g AppleInterfaceStyleSwitchesAutomatically 2>/dev/null

t=$(cat "$BKP/dock-tilesize.txt" 2>/dev/null || echo 64)
defaults write com.apple.dock tilesize -int "${t:-64}"
m=$(cat "$BKP/dock-magnification.txt" 2>/dev/null || echo 0)
[ "$m" = "1" ] && defaults write com.apple.dock magnification -bool true || defaults write com.apple.dock magnification -bool false
defaults delete com.apple.dock largesize 2>/dev/null

sed -i '' '/about-gg=/d' "$HOME/.zshrc" 2>/dev/null || true
killall Dock 2>/dev/null; killall Finder 2>/dev/null
echo "Tahoe appearance restored."
