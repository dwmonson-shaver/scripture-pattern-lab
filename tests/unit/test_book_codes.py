"""Tests for ``src/ontology/book_codes.py``.

Closes Bucket 3 (book-id normalization). The silent-miss guard is
``test_canonical_07_examples_all_resolve``: if a future canonical edit
adds an abbreviation to DSL examples without updating ``_ABBREV_TO_BB``,
this test fails loudly.
"""

from __future__ import annotations

import pytest

from src.ontology.book_codes import (
    _ABBREV_TO_BB,
    _BB_TO_DISPLAY,
    bb_to_display,
    book_abbrev_to_bb,
)


def test_all_27_books_mapped() -> None:
    assert len(_ABBREV_TO_BB) == 27
    assert len(_BB_TO_DISPLAY) == 27


def test_round_trip() -> None:
    """Every abbreviation maps to a BB that has a non-empty display name."""
    abbrev_by_bb: dict[str, str] = {}
    for abbrev, bb in _ABBREV_TO_BB.items():
        # Each BB should appear exactly once in the abbrev map.
        assert bb not in abbrev_by_bb, f"BB {bb} appears twice in _ABBREV_TO_BB"
        abbrev_by_bb[bb] = abbrev
        assert _BB_TO_DISPLAY[bb], f"BB {bb} has empty display name"
    # Round-trip: every BB in _BB_TO_DISPLAY also appears in _ABBREV_TO_BB.
    assert set(abbrev_by_bb.keys()) == set(_BB_TO_DISPLAY.keys())


def test_book_abbrev_to_bb_known() -> None:
    assert book_abbrev_to_bb("rom") == "06"
    assert book_abbrev_to_bb("1cor") == "07"
    assert book_abbrev_to_bb("3jn") == "25"


def test_book_abbrev_to_bb_case_insensitive() -> None:
    assert book_abbrev_to_bb("ROM") == "06"
    assert book_abbrev_to_bb("Rom") == "06"


def test_book_abbrev_to_bb_raises_on_unknown() -> None:
    with pytest.raises(KeyError, match="unknown book abbreviation"):
        book_abbrev_to_bb("xyz")


def test_bb_to_display_spot_check() -> None:
    assert bb_to_display("07") == "1Cor"
    assert bb_to_display("25") == "3Jn"
    assert bb_to_display("06") == "Rom"


def test_bb_to_display_raises_on_unknown() -> None:
    with pytest.raises(KeyError, match="unknown BB code"):
        bb_to_display("99")


def test_canonical_07_examples_all_resolve() -> None:
    """Silent-miss guard from the design's risks section.

    Every abbreviation listed in ``book:rom,1cor,2cor,gal,eph,php,col,
    1th,2th,1ti,2ti,tit,phm`` (canonical-07 example 8 line 367) must
    resolve without raising.
    """
    canonical_07_example_8 = [
        "rom",
        "1cor",
        "2cor",
        "gal",
        "eph",
        "php",
        "col",
        "1th",
        "2th",
        "1ti",
        "2ti",
        "tit",
        "phm",
    ]
    for abbrev in canonical_07_example_8:
        # Should not raise.
        bb = book_abbrev_to_bb(abbrev)
        # And should round-trip through display.
        assert bb_to_display(bb)
