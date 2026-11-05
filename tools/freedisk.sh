#!/bin/bash
# Make room on a GitHub macOS runner. Keeps the selected Xcode (python3
# and xcrun go through it); removes other Xcodes and the Android SDK.
set -u
avail() { df -g / | awk 'NR==2 {print $4}'; }
echo "free before: $(avail) GB"
SEL=$(xcode-select -p 2>/dev/null | sed 's#/Contents/Developer$##')
if [ -z "$SEL" ]; then
  echo "xcode-select -p failed; refusing to delete Xcode apps" >&2
  exit 1
fi
SEL_REAL=$(cd "$SEL" 2>/dev/null && pwd -P)
for x in /Applications/Xcode*.app; do
  [ -d "$x" ] || continue
  real=$(cd "$x" && pwd -P)
  if [ "$real" != "$SEL_REAL" ] && [ ! -L "$x" ]; then
    echo "removing $x"
    sudo rm -rf "$x"
  fi
done
sudo rm -rf "$HOME/Library/Android" "$HOME/hostedtoolcache/CodeQL" 2>/dev/null
echo "selected Xcode: $SEL"
echo "free after: $(avail) GB"
python3 -c 'print("python3 ok")'
