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

- `translations/kjv/` — public-domain KJV New Testament (Slice 1, DEC-128/144)
  - Source: [aruljohn/Bible-kjv](https://github.com/aruljohn/Bible-kjv) (public domain)
  - 27 per-book JSON files, shape `{"book","chapters":[{"chapter","verses":[{"verse","text"}]}]}`
  - Verse-aligned to the Greek corpus by (corpus_id, book BB, chapter, verse)
  - `translations/_kjv-src/` is the working clone (the fetch script copies the
    27 NT books into `translations/kjv/`)
  - License: Public Domain (KJV text)

## How to fetch

```bash
./scripts/ingest/fetch_morphgnt.sh      # Greek corpus
./scripts/ingest/fetch_kjv.sh           # KJV English translation (Slice 1)
```

Both scripts are idempotent — re-running pulls upstream changes instead
of re-cloning.
