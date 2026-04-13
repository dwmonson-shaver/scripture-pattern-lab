# /commit — Stage and Commit Changes

You are creating a git commit for the current changes. This is a simple, focused command — staging and committing only.

## Process

1. Run `git status` to see all changes (staged and unstaged).
2. Run `git diff` to see what changed.
3. Run `git log --oneline -5` to see recent commit message style.
4. Draft a commit message:
   - Imperative mood ("Add parser types" not "Added parser types")
   - Explain WHY, not WHAT
   - One-line summary, optional body for context
5. Stage the relevant files (prefer specific files over `git add -A`).
6. Present the commit message to the human for approval.
7. Commit.

## Rules

- Do NOT stage files that contain secrets (.env, credentials).
- Do NOT use `git add -A` or `git add .` — stage specific files by name.
- Do NOT update governance files (decision-log, spec-coverage) — that's `/review`.
- Do NOT extract or present decisions — that's `/review`.
- Keep it simple: diff, message, stage, commit.
