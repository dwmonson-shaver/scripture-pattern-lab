# Fonts

This directory holds self-hosted source-language fonts referenced from
`assets/styles/globals.css` via `@font-face`. All three SBL font binaries
are bundled with the repo; only the Greek file is wired up in CSS at MVP.

## Bundled fonts

### `SBLGreek.woff2`  (wired up)

Polytonic Greek font from the Society of Biblical Literature. Loaded by
the `@font-face { font-family: 'SBL Greek'; ... }` rule and used by the
`.text-grc` class.

- Download: https://www.sbl-site.org/resources/fonts/
- License: free for academic / non-commercial use. Verify the
  redistribution terms for your deployment context before shipping a
  public instance.
- Conversion (TTF → WOFF2):

  ```bash
  pip install fonttools brotli   # or `uv pip install fonttools brotli`
  pyftsubset SBL_grk.ttf --flavor=woff2 --output-file=SBLGreek.woff2 --unicodes='*'
  ```

- Served by the deployed Worker at `/fonts/SBLGreek.woff2`.

### `SBLHebrew.woff2`  (bundled, unused at MVP)

The corpus is currently New-Testament-only (Koine Greek). The
`.text-heb` class in `globals.css` already exists as a hook for future
Hebrew rendering but no `@font-face` rule loads the file yet — that
declaration lands with the slice that introduces OT corpus / Hebrew
display.

- Source TTF: `SBL_Hbrw.ttf` from the same SBL fonts page.
- Conversion: same `pyftsubset --flavor=woff2 --unicodes='*'` pipeline.

### `SBLBibLit.woff2`  (bundled, unused at MVP)

SBL BibLit is a unified font containing both polytonic Greek and pointed
Hebrew glyphs in one file. Useful as a single-source-language fallback
or for mixed-script display. Not currently referenced by any CSS rule.

- Source TTF: `SBL_BLit.ttf` from the same SBL fonts page.
- Conversion: same `pyftsubset --flavor=woff2 --unicodes='*'` pipeline.
