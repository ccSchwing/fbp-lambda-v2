#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYPROJECT="$ROOT_DIR/src/FBPLib/pyproject.toml"
OUT_FILE="$ROOT_DIR/src/FBPLib-Layer/requirements.txt"
SOURCE_LIB_DIR="$ROOT_DIR/src/FBPLib"
LAYER_LIB_DIR="$ROOT_DIR/src/FBPLib-Layer/FBPLib"

if [[ ! -f "$PYPROJECT" ]]; then
  echo "Missing pyproject file: $PYPROJECT" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT_FILE")"

awk '
  /^[[:space:]]*\[project\][[:space:]]*$/ { in_project = 1; next }
  /^[[:space:]]*\[/ && in_project { in_project = 0 }
  in_project && /^[[:space:]]*dependencies[[:space:]]*=[[:space:]]*\[/ { in_deps = 1; next }
  in_deps && /\]/ { in_deps = 0; exit }
  in_deps {
    line = $0
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
    gsub(/,/, "", line)
    gsub(/"/, "", line)
    if (line != "") print line
  }
' "$PYPROJECT" > "$OUT_FILE"

# Mirror shared source into layer as real files so --use-container builds don't break on symlinks.
rm -rf "$LAYER_LIB_DIR"
mkdir -p "$LAYER_LIB_DIR"

if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete --exclude '__pycache__' --exclude '*.pyc' "$SOURCE_LIB_DIR/" "$LAYER_LIB_DIR/"
else
  cp -R "$SOURCE_LIB_DIR/." "$LAYER_LIB_DIR/"
  find "$LAYER_LIB_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
  find "$LAYER_LIB_DIR" -type f -name '*.pyc' -delete
fi

echo "Wrote $(wc -l < "$OUT_FILE" | tr -d ' ') dependencies to $OUT_FILE and synced FBPLib sources"
exit 0