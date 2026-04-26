#!/usr/bin/env bash
# Fetch the MorphGNT/SBLGNT corpus into data/raw/morphgnt-sblgnt/.
# Idempotent: clones on first run, fast-forward pulls on subsequent runs.

set -euo pipefail

REPO_URL="https://github.com/morphgnt/sblgnt.git"
TARGET_DIR="data/raw/morphgnt-sblgnt"

# Run from repo root regardless of where the script is invoked from.
cd "$(git rev-parse --show-toplevel)"

if [ -d "$TARGET_DIR/.git" ]; then
  echo "Updating existing MorphGNT clone..."
  git -C "$TARGET_DIR" pull --ff-only
else
  echo "Cloning MorphGNT into $TARGET_DIR ..."
  mkdir -p "$(dirname "$TARGET_DIR")"
  git clone --depth 1 "$REPO_URL" "$TARGET_DIR"
fi

book_count=$(find "$TARGET_DIR" -maxdepth 1 -name '*.txt' | wc -l | tr -d ' ')
token_count=$(find "$TARGET_DIR" -maxdepth 1 -name '*.txt' -exec cat {} + | wc -l | tr -d ' ')

echo
echo "MorphGNT fetch complete:"
echo "  books:  $book_count (expected 27)"
echo "  tokens: $token_count (expected ~138K)"
