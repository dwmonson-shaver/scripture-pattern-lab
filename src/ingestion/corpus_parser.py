"""MorphGNT corpus parser — converts on-disk MorphGNT data files into CorpusToken records.

Mirrors src/engine/parser.py discipline: function-style public API, frozen Pydantic v2
model, custom exception with (message, line_no, source) shape. No DB, no IO beyond
reading the on-disk text files.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class CorpusToken(BaseModel):
    """One row from a MorphGNT data file, normalized for storage."""

    model_config = ConfigDict(frozen=True)

    book: str
    chapter: int
    verse: int
    position: int
    global_position: int
    surface_form: str
    normalized_form: str
    lemma: str
    morph_code: str
    pos: str
    language: str = "grc"
    corpus_id: str = "nt"


class CorpusParseError(Exception):
    """Raised when a MorphGNT row cannot be parsed."""

    def __init__(self, message: str, line_no: int, source: str) -> None:
        self.line_no = line_no
        self.source = source
        super().__init__(f"{message} (at line {line_no} of {source})")


_BOOK_NUMBER_BY_FILENAME: dict[str, str] = {
    "61-Mt-morphgnt.txt": "01",
    "62-Mk-morphgnt.txt": "02",
    "63-Lk-morphgnt.txt": "03",
    "64-Jn-morphgnt.txt": "04",
    "65-Ac-morphgnt.txt": "05",
    "66-Ro-morphgnt.txt": "06",
    "67-1Co-morphgnt.txt": "07",
    "68-2Co-morphgnt.txt": "08",
    "69-Ga-morphgnt.txt": "09",
    "70-Eph-morphgnt.txt": "10",
    "71-Php-morphgnt.txt": "11",
    "72-Col-morphgnt.txt": "12",
    "73-1Th-morphgnt.txt": "13",
    "74-2Th-morphgnt.txt": "14",
    "75-1Ti-morphgnt.txt": "15",
    "76-2Ti-morphgnt.txt": "16",
    "77-Tit-morphgnt.txt": "17",
    "78-Phm-morphgnt.txt": "18",
    "79-Heb-morphgnt.txt": "19",
    "80-Jas-morphgnt.txt": "20",
    "81-1Pe-morphgnt.txt": "21",
    "82-2Pe-morphgnt.txt": "22",
    "83-1Jn-morphgnt.txt": "23",
    "84-2Jn-morphgnt.txt": "24",
    "85-3Jn-morphgnt.txt": "25",
    "86-Jud-morphgnt.txt": "26",
    "87-Re-morphgnt.txt": "27",
}


def parse_corpus_line(
    line: str,
    line_no: int,
    source: str,
    *,
    position: int,
    global_position: int,
) -> CorpusToken:
    """Parse one space-delimited MorphGNT row into a CorpusToken.

    The caller supplies position (1-based, per-verse) and global_position (1-based,
    corpus-wide); these are state the row alone does not carry.
    """
    fields = line.rstrip("\n").split(" ")
    if len(fields) != 7:
        raise CorpusParseError(
            f"expected 7 space-delimited columns, got {len(fields)}: {line!r}",
            line_no=line_no,
            source=source,
        )

    bbccvv, pos_code, morph_code, surface_form, _text_no_punct, normalized_form, lemma = fields

    if len(bbccvv) != 6 or not bbccvv.isdigit():
        raise CorpusParseError(
            f"expected 6-digit BBCCVV, got {bbccvv!r}",
            line_no=line_no,
            source=source,
        )

    return CorpusToken(
        book=bbccvv[0:2],
        chapter=int(bbccvv[2:4]),
        verse=int(bbccvv[4:6]),
        position=position,
        global_position=global_position,
        surface_form=surface_form,
        normalized_form=normalized_form,
        lemma=lemma,
        morph_code=morph_code,
        pos=pos_code,
    )


def parse_corpus_file(
    path: str | Path,
    *,
    start_global_position: int = 1,
) -> Iterator[CorpusToken]:
    """Yield CorpusToken records for every data row in one MorphGNT file.

    position resets to 1 at each new BBCCVV; global_position increments monotonically
    starting from start_global_position.
    """
    path = Path(path)
    source = str(path)
    global_position = start_global_position
    current_bbccvv: str | None = None
    position = 0

    with path.open(encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            stripped = raw_line.rstrip("\n")
            if not stripped:
                continue

            bbccvv = stripped[:6]
            if bbccvv != current_bbccvv:
                position = 1
                current_bbccvv = bbccvv
            else:
                position += 1

            yield parse_corpus_line(
                stripped,
                line_no=line_no,
                source=source,
                position=position,
                global_position=global_position,
            )
            global_position += 1


def parse_corpus_directory(
    directory: str | Path,
) -> Iterator[CorpusToken]:
    """Yield CorpusToken records for all 27 MorphGNT files in canonical book order
    (BB 01 → 27), threading global_position across files.
    """
    directory = Path(directory)
    global_position = 1
    for filename in sorted(
        _BOOK_NUMBER_BY_FILENAME, key=_BOOK_NUMBER_BY_FILENAME.__getitem__
    ):
        path = directory / filename
        for token in parse_corpus_file(path, start_global_position=global_position):
            yield token
            global_position = token.global_position + 1
