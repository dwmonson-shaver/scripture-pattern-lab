# Raw Corpus Data

This directory holds upstream corpus sources, fetched on demand. Contents
are gitignored (this README is the only tracked file) — the data has its
own license and is reproducibly retrievable, so checking it in would only
duplicate the upstream and complicate license tracking.

## What gets fetched here

- `morphgnt-sblgnt/` — clone of [morphgnt/sblgnt](https://github.com/morphgnt/sblgnt)
  - SBLGNT Greek New Testament with MorphGNT morphological annotations
  - 27 TSV files, one per book, ~138K tokens total
  - Format per row: `book/chapter/verse  part-of-speech  parse-code  text  word  normalized  lemma`
  - License: MorphGNT annotations under CC BY-SA 3.0; SBLGNT text under SBLGNT EULA (free non-commercial use)

## How to fetch

```bash
./scripts/ingest/fetch_morphgnt.sh
```

The script is idempotent — re-running it pulls upstream changes instead
of re-cloning.
