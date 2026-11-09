#!/bin/bash
# make.sh <repo-root> <out-dir> [docbase]  → <out-dir>/КІБР
set -e
R="$1"; O="$2"; DB="$3"; P="$R/src/pkg"; K="$O/КІБР"
rm -rf "$K"; mkdir -p "$K/КІБР.app/Contents/MacOS" "$K/КІБР.app/Contents/Resources" "$K/kibr-data"
cp "$P/Info.plist" "$K/КІБР.app/Contents/"; cp "$P/kibr.sh" "$K/КІБР.app/Contents/MacOS/kibr"; chmod 755 "$K/КІБР.app/Contents/MacOS/kibr"
cp "$P/AppIcon.icns" "$K/КІБР.app/Contents/Resources/"; printf 'APPL????' > "$K/КІБР.app/Contents/PkgInfo"
cp "$P/open.html" "$K/Відкрити КІБР.html"; cp "$P/windows.cmd" "$K/КІБР (Windows).cmd"; cp "$P/readme.txt" "$K/Як запустити.txt"
for d in index.html manifest.webmanifest audio fonts icons vendor; do cp -R "$R/$d" "$K/kibr-data/"; done
if [ -n "$DB" ]; then sed -i.bak "s#<script>#<script>window.KB_DOCBASE=\"$DB\";</script><script>#" "$K/kibr-data/index.html" 2>/dev/null; rm -f "$K/kibr-data/index.html.bak"
else cp -R "$R/docs" "$K/kibr-data/"; fi
echo done "$K"
