# Fonts

This directory holds self-hosted source-language fonts referenced from
`assets/styles/globals.css` via `@font-face`.

## Required files

### `SBLGreek.woff2`

Polytonic Greek font from the Society of Biblical Literature.

- Download: https://www.sbl-site.org/educational/biblicalfonts.aspx
- License: free for academic / non-commercial use. Verify the redistribution terms for your deployment context before shipping a public instance.
- The site delivers `.zip` with an OTF/TTF; convert to `.woff2` for web delivery:

  ```bash
  # Using fonttools (https://github.com/fonttools/fonttools):
  pip install fonttools brotli
  pyftsubset SBL_Grk.ttf --flavor=woff2 --output-file=SBLGreek.woff2 --unicodes='*'
  ```

- Place the resulting `SBLGreek.woff2` in this directory; the deployed Worker serves it at `/fonts/SBLGreek.woff2`.

### `SBLHebrew.woff2` (not required at MVP)

The corpus is currently New-Testament-only (Koine Greek). The
`@font-face { font-family: 'SBL Hebrew'; ... }` rule and the `.text-heb`
class exist as hooks for future Hebrew rendering; no font file is shipped
in S1. When the OT corpus loads, this directory needs `SBLHebrew.woff2`
following the same pipeline.
