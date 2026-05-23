#!/usr/bin/env bash
# Fix Codex CLI ~/.codex/sessions permissions.
#
# Bucket 5: Codex has been blocked by ~/.codex/sessions permissions across
# four consecutive slices (E, F, J1, K). All four close reviews ran as
# claude-fallback flavor instead.
#
# Diagnosis: lsof / ownership inspection during Slice K showed
# ~/.codex/sessions itself is owned by $(whoami):staff with normal perms, so
# the "permissions" message from the Codex companion runtime is most likely
# a stale lock file or a misnamed open-handle conflict inside a session
# subdir (2026/MM/DD/...). Defensive fix: rechown everything, ensure rwx for
# the owner, remove any stale lock files, then probe with a no-op codex
# invocation.
#
# Safe to run multiple times. Idempotent.
#
# Usage:
#   bash scripts/fix-codex-permissions.sh
#   (will prompt for sudo password once for the chown step)

set -euo pipefail

CODEX_DIR="$HOME/.codex"
SESSIONS_DIR="$CODEX_DIR/sessions"

if [ ! -d "$CODEX_DIR" ]; then
  echo "FAIL: $CODEX_DIR does not exist. Is Codex CLI installed?"
  exit 1
fi

if [ ! -d "$SESSIONS_DIR" ]; then
  echo "INFO: $SESSIONS_DIR does not exist; creating it."
  mkdir -p "$SESSIONS_DIR"
fi

echo "=== Step 1: Current state ==="
ls -ld "$CODEX_DIR" "$SESSIONS_DIR"
echo ""
echo "Non-owner files under $SESSIONS_DIR (should be empty):"
find "$SESSIONS_DIR" -not -user "$(whoami)" -print 2>/dev/null | head -20 || true
echo ""
echo "Files without owner-rw under $SESSIONS_DIR (should be empty):"
find "$SESSIONS_DIR" ! -perm -u+rw -print 2>/dev/null | head -20 || true
echo ""

echo "=== Step 2: Stale lock-file scan ==="
LOCK_FILES=$(find "$SESSIONS_DIR" -name "*.lock" -o -name ".lock*" 2>/dev/null || true)
if [ -n "$LOCK_FILES" ]; then
  echo "Found stale lock files:"
  echo "$LOCK_FILES"
  echo ""
  read -p "Delete them? [y/N] " -r REPLY
  if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    echo "$LOCK_FILES" | xargs rm -f
    echo "  Deleted."
  else
    echo "  Skipped."
  fi
else
  echo "  No stale lock files found."
fi
echo ""

echo "=== Step 3: Chown + chmod (requires sudo) ==="
echo "Running: sudo chown -R \"$(whoami):staff\" \"$CODEX_DIR\""
sudo chown -R "$(whoami):staff" "$CODEX_DIR"
echo "  Done."

echo "Running: chmod -R u+rwX \"$SESSIONS_DIR\""
chmod -R u+rwX "$SESSIONS_DIR"
echo "  Done."
echo ""

echo "=== Step 4: Verify ==="
ls -ld "$CODEX_DIR" "$SESSIONS_DIR"
echo ""
NON_OWNED=$(find "$SESSIONS_DIR" -not -user "$(whoami)" -print 2>/dev/null | wc -l | tr -d ' ')
if [ "$NON_OWNED" != "0" ]; then
  echo "FAIL: $NON_OWNED files still not owned by $(whoami)."
  exit 1
fi
NON_RW=$(find "$SESSIONS_DIR" ! -perm -u+rw -print 2>/dev/null | wc -l | tr -d ' ')
if [ "$NON_RW" != "0" ]; then
  echo "FAIL: $NON_RW files still lack owner rw."
  exit 1
fi
echo "  All files under $SESSIONS_DIR owned by $(whoami) with owner rw. OK."
echo ""

echo "=== Step 5: Codex smoke test ==="
if command -v codex >/dev/null 2>&1; then
  echo "Running: codex --help (no-op smoke test)"
  codex --help > /dev/null 2>&1 && echo "  codex --help: OK" || echo "  codex --help: failed (check Codex install separately)"
else
  echo "  codex CLI not on PATH; skipping smoke test."
  echo "  Install per Codex CLI install docs if needed."
fi
echo ""

echo "=== Done ==="
echo ""
echo "If Bucket 5 still blocks during the next /codex:rescue, the issue is"
echo "not filesystem permissions. Capture the exact error message and"
echo "stderr from the failing run; the next diagnostic step is the Codex"
echo "companion runtime's own session-locking logic, not ~/.codex perms."
