#!/usr/bin/env bash
# Fetch a public-domain KJV New Testament (per-book JSON) into
# data/raw/translations/kjv/.
#
# Source: aruljohn/Bible-kjv (public domain KJV text, one JSON file per book in
# the shape {"book","chapters":[{"chapter","verses":[{"verse","text"}]}]}).
# Slice 1 only needs the 27 NT books; the parser ignores any non-NT file by
# raising on an unrecognized book name, so we fetch only the NT books here.
#
# Idempotent: clones on first run, fast-forward pulls on subsequent runs, then
# copies the 27 NT book JSON files into the target dir.

set -euo pipefail

REPO_URL="https://github.com/aruljohn/Bible-kjv.git"
CLONE_DIR="data/raw/translations/_kjv-src"
TARGET_DIR="data/raw/translations/kjv"

cd "$(git rev-parse --show-toplevel)"

if [ -d "$CLONE_DIR/.git" ]; then
  echo "Updating existing KJV clone..."
  git -C "$CLONE_DIR" pull --ff-only
else
  echo "Cloning KJV source into $CLONE_DIR ..."
  mkdir -p "$(dirname "$CLONE_DIR")"
  git clone --depth 1 "$REPO_URL" "$CLONE_DIR"
fi

mkdir -p "$TARGET_DIR"

# The 27 NT books, by the source repo's filenames.
NT_BOOKS=(
  Matthew Mark Luke John Acts Romans 1Corinthians 2Corinthians Galatians
  Ephesians Philippians Colossians 1Thessalonians 2Thessalonians 1Timothy
  2Timothy Titus Philemon Hebrews James 1Peter 2Peter 1John 2John 3John Jude
  Revelation
)

copied=0
for book in "${NT_BOOKS[@]}"; do
  src="$CLONE_DIR/$book.json"
  if [ -f "$src" ]; then
    cp "$src" "$TARGET_DIR/$book.json"
    copied=$((copied + 1))
  else
    echo "WARN: expected NT book file not found: $src" >&2
  fi
done

echo
echo "KJV fetch complete:"
echo "  NT book files copied: $copied (expected 27) -> $TARGET_DIR"
echo
echo "Next: ./scripts/db/apply_schemas.sh && python scripts/db/ingest_translation.py"
