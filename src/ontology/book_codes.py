"""Book-id normalization between DSL abbreviations and stored BB codes.

Closes Bucket 3 (book-id normalization) per
``docs/governance/reviews-log.md``: the DSL parser produces lowercase
abbreviations (``"rom"``, ``"1cor"``, ``"3jn"``) while the ``tokens.book``
column stores 2-digit BB codes (``"06"``, ``"07"``, ``"25"``) per DEC-026.
This module is the single canonical translation layer between the two
forms; it raises ``KeyError`` on unknown abbreviations / codes rather than
silently miss (per the "no slop" / REQ:08.apparatus-marks discipline).

The 27-book NT mapping mirrors MorphGNT's BBCCVV row-prefix ordering as
realized in ``src/ingestion/corpus_parser.py:_BOOK_NUMBER_BY_FILENAME``.
The display strings (``"1Cor"``, ``"3Jn"``, ``"Rom"``) are the canonical
short forms used in ``MatchCandidate.reference`` (see canonical-09 §5).
"""

from __future__ import annotations

# DSL abbreviation (lowercase) -> 2-digit BB code stored in tokens.book.
#
# Abbreviation forms are the canonical lowercase forms from
# docs/canonical/07_query-to-ast-examples.md (example 8). BB codes match
# src/ingestion/corpus_parser.py:_BOOK_NUMBER_BY_FILENAME.
_ABBREV_TO_BB: dict[str, str] = {
    "mat": "01",
    "mar": "02",
    "luk": "03",
    "joh": "04",
    "act": "05",
    "rom": "06",
    "1cor": "07",
    "2cor": "08",
    "gal": "09",
    "eph": "10",
    "php": "11",
    "col": "12",
    "1th": "13",
    "2th": "14",
    "1ti": "15",
    "2ti": "16",
    "tit": "17",
    "phm": "18",
    "heb": "19",
    "jas": "20",
    "1pe": "21",
    "2pe": "22",
    "1jn": "23",
    "2jn": "24",
    "3jn": "25",
    "jud": "26",
    "rev": "27",
}


# 2-digit BB code -> display name used in MatchCandidate.reference strings
# such as ``"1Cor 13:13"``.
_BB_TO_DISPLAY: dict[str, str] = {
    "01": "Mat",
    "02": "Mar",
    "03": "Luk",
    "04": "Joh",
    "05": "Act",
    "06": "Rom",
    "07": "1Cor",
    "08": "2Cor",
    "09": "Gal",
    "10": "Eph",
    "11": "Php",
    "12": "Col",
    "13": "1Th",
    "14": "2Th",
    "15": "1Ti",
    "16": "2Ti",
    "17": "Tit",
    "18": "Phm",
    "19": "Heb",
    "20": "Jas",
    "21": "1Pe",
    "22": "2Pe",
    "23": "1Jn",
    "24": "2Jn",
    "25": "3Jn",
    "26": "Jud",
    "27": "Rev",
}


def book_abbrev_to_bb(abbrev: str) -> str:
    """Translate a DSL book abbreviation to its 2-digit BB code.

    Case-insensitive on the input (``"ROM"``, ``"Rom"``, and ``"rom"`` all
    resolve to ``"06"``). Raises ``KeyError`` on unknown abbreviation —
    silent miss is worse than no result (Bucket 3 discipline).
    """
    key = abbrev.lower()
    if key not in _ABBREV_TO_BB:
        raise KeyError(f"unknown book abbreviation: {abbrev}")
    return _ABBREV_TO_BB[key]


def bb_to_display(bb: str) -> str:
    """Translate a 2-digit BB code to its display name (e.g. ``"1Cor"``).

    Raises ``KeyError`` on unknown code — same loud-failure policy as
    :func:`book_abbrev_to_bb`.
    """
    if bb not in _BB_TO_DISPLAY:
        raise KeyError(f"unknown BB code: {bb}")
    return _BB_TO_DISPLAY[bb]
