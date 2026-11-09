#!/bin/bash
# КІБР · офлайн. Відкриває курс у Google Chrome без інтернету.
HERE="$(cd "$(dirname "$0")/../../.." && pwd)"
APP="$(cd "$(dirname "$0")/.." && pwd)"
F="$HERE/kibr-data/index.html"
[ -f "$F" ] || F="$APP/Resources/kibr-data/index.html"
if [ ! -f "$F" ]; then
  osascript -e 'display dialog "Не знайдено папку kibr-data. Скопіюйте папку КІБР цілком (значок КІБР і папку kibr-data разом)." buttons {"OK"} with icon caution with title "КІБР"' >/dev/null 2>&1
  exit 1
fi
if open -Ra "Google Chrome" >/dev/null 2>&1; then
  open -a "Google Chrome" "$F"
else
  open "$F"
fi
