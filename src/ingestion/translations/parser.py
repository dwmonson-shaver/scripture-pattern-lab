"""Parser for per-book English-translation JSON into verse-aligned rows.

Slice 1 (DEC-128/144). Reads the widely-mirrored public-domain KJV JSON shape
(one file per book) used by e.g. ``aruljohn/Bible-kjv``::

    {"book": "Romans",
     "chapters": [{"chapter": "1",
                   "verses": [{"verse": "1", "text": "Paul, a servant..."}]}]}

Book names are mapped to the 2-digit BB codes stored in ``tokens.book`` (and
``translation_verses.book``) so English verses align to the Greek corpus. Only
the 27 NT books are recognized in Slice 1 (corpus is NT-only); an unrecognized
book name raises ``TranslationParseError`` rather than silently dropping verses
(the project's no-slop / loud-failure discipline).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict

# Full English book name (as it appears in KJV JSON sources) -> 2-digit BB code.
# Mirrors src/ontology/book_codes.py:_ABBREV_TO_BB (same BB codes), keyed by the
# canonical full name AND common spacing/abbreviation variants seen across KJV
# JSON mirrors (e.g. "1Corinthians", "1 Corinthians", "I Corinthians").
_BOOK_NAME_TO_BB: dict[str, str] = {
    "matthew": "01",
    "mark": "02",
    "luke": "03",
    "john": "04",
    "acts": "05",
    "romans": "06",
    "1corinthians": "07",
    "2corinthians": "08",
    "galatians": "09",
    "ephesians": "10",
    "philippians": "11",
    "colossians": "12",
    "1thessalonians": "13",
    "2thessalonians": "14",
    "1timothy": "15",
    "2timothy": "16",
    "titus": "17",
    "philemon": "18",
    "hebrews": "19",
    "james": "20",
    "1peter": "21",
    "2peter": "22",
    "1john": "23",
    "2john": "24",
    "3john": "25",
    "jude": "26",
    "revelation": "27",
    # common variant: KJV mirrors sometimes title Revelation "Revelation of John"
    "revelationofjohn": "27",
}


class TranslationParseError(Exception):
    """Raised when a translation source file cannot be parsed into verses."""

    def __init__(self, message: str, source: str) -> None:
        super().__init__(f"{message} (source={source})")
        self.source = source


class TranslationVerse(BaseModel):
    """One verse of a translation, aligned to the corpus by (book BB, ch, v)."""

    model_config = ConfigDict(frozen=True)

    corpus_id: str = "nt"
    book: str  # 2-digit BB code
    chapter: int
    verse: int
    text: str


def book_name_to_bb(name: str) -> str:
    """Map an English book name (any common spacing/case) to its BB code.

    Strips whitespace, lowercases, drops dots, and normalizes leading roman
    numerals (``"I "``/``"II "``/``"III "``) to arabic so ``"I Corinthians"``,
    ``"1 Corinthians"``, and ``"1Corinthians"`` all resolve to ``"07"``. Raises
    ``KeyError`` on an unrecognized name.
    """
    key = name.strip().lower().replace(".", "")
    for roman, arabic in (("iii ", "3"), ("ii ", "2"), ("i ", "1")):
        if key.startswith(roman):
            key = arabic + key[len(roman) :]
            break
    key = key.replace(" ", "")
    if key not in _BOOK_NAME_TO_BB:
        raise KeyError(f"unrecognized translation book name: {name!r}")
    return _BOOK_NAME_TO_BB[key]


def parse_translation_file(
    path: str | Path,
    *,
    corpus_id: str = "nt",
) -> Iterator[TranslationVerse]:
    """Yield TranslationVerse rows from one per-book KJV-shape JSON file.

    Raises TranslationParseError on malformed JSON, a missing/unknown ``book``
    name, or a chapter/verse number that is not an integer string.
    """
    source = str(path)
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TranslationParseError(f"cannot read JSON: {exc}", source) from exc

    book_name = raw.get("book")
    if not isinstance(book_name, str) or not book_name.strip():
        raise TranslationParseError("missing 'book' name", source)
    try:
        book_bb = book_name_to_bb(book_name)
    except KeyError as exc:
        raise TranslationParseError(str(exc), source) from exc

    chapters = raw.get("chapters")
    if not isinstance(chapters, list):
        raise TranslationParseError("missing or non-list 'chapters'", source)

    for ch in chapters:
        try:
            chapter_no = int(ch["chapter"])
        except (KeyError, TypeError, ValueError) as exc:
            raise TranslationParseError(
                f"bad chapter number: {ch.get('chapter')!r}", source
            ) from exc
        verses = ch.get("verses")
        if not isinstance(verses, list):
            raise TranslationParseError(
                f"chapter {chapter_no} missing 'verses' list", source
            )
        for v in verses:
            try:
                verse_no = int(v["verse"])
                text = v["text"]
            except (KeyError, TypeError, ValueError) as exc:
                raise TranslationParseError(
                    f"bad verse in chapter {chapter_no}: {v!r}", source
                ) from exc
            if not isinstance(text, str):
                raise TranslationParseError(
                    f"non-string text at {chapter_no}:{verse_no}", source
                )
            yield TranslationVerse(
                corpus_id=corpus_id,
                book=book_bb,
                chapter=chapter_no,
                verse=verse_no,
                text=text,
            )


def parse_translation_directory(
    directory: str | Path,
    *,
    corpus_id: str = "nt",
) -> Iterator[TranslationVerse]:
    """Yield TranslationVerse rows from every ``*.json`` file in a directory.

    Files are processed in sorted filename order. Any file whose ``book`` name
    is not a recognized NT book raises TranslationParseError (loud failure).
    """
    for path in sorted(Path(directory).glob("*.json")):
        yield from parse_translation_file(path, corpus_id=corpus_id)
