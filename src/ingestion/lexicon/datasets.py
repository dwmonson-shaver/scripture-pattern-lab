"""Parsers for the three self-hosted lexicon datasets (Slice N, DEC-103).

Each parser is a pure file→typed-row iterator (the corpus-parser discipline:
file IO + mapping, no DB, no logging). Strong's numbers are normalized across
all three sources to a single canonical form — ``G`` + 4-zero-padded digits
plus any trailing disambiguation letter (e.g. ``G0026``, ``G2264G``) — so the
bridge and gloss tables join cleanly.

Dataset formats (samples in tests/fixtures/lexicon/):
  * jtauber lexemes.yaml — YAML mapping keyed by MorphGNT lemma; each entry has
    a ``strongs`` field (bare int, may be missing). The KEY is the corpus lemma.
  * TBESG ...txt — tab-separated; a long prose header precedes data rows. Data
    rows start with an EStrong# like ``G0001``. Fields (0-indexed):
    0=eStrong, 3=unicode Greek, 4=transliteration, 5=morph, 6=short gloss.
  * Dodson dodson.tsv — tab-separated with a header row; columns:
    0=Strong's (bare zero-padded), 2=Greek (beta code), 3=brief English def.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Typed rows
# ---------------------------------------------------------------------------


class LemmaStrongs(BaseModel):
    """One jtauber bridge row: a MorphGNT lemma and a Strong's number."""

    model_config = ConfigDict(frozen=True)

    morphgnt_lemma: str
    strongs: str


class StrongsGloss(BaseModel):
    """One Strong's → English-gloss row (TBESG or Dodson)."""

    model_config = ConfigDict(frozen=True)

    strongs: str
    lemma: str | None
    gloss: str
    source: str  # 'tbesg' | 'dodson'


# ---------------------------------------------------------------------------
# Strong's normalization
# ---------------------------------------------------------------------------

_STRONGS_RE = re.compile(r"^G?0*(\d+)([A-Za-z]?)$")


def normalize_strongs(raw: str) -> str | None:
    """Normalize a Strong's token to ``G`` + 4-zero-padded digits + suffix.

    ``2`` → ``G0002``; ``0026`` → ``G0026``; ``G0001`` → ``G0001``;
    ``G2264G`` → ``G2264G``. Returns ``None`` for empty/non-numeric input so
    callers can skip rows with no usable Strong's.
    """
    token = (raw or "").strip()
    if not token:
        return None
    match = _STRONGS_RE.match(token)
    if match is None:
        return None
    digits, suffix = match.group(1), match.group(2)
    return f"G{int(digits):04d}{suffix.upper()}"


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def parse_jtauber_mappings(path: Path) -> Iterator[LemmaStrongs]:
    """Yield ``LemmaStrongs`` rows from the jtauber lexemes.yaml file.

    The file is a flat YAML mapping ``lemma:`` → indented ``key: value`` lines.
    We parse it line-orientedly (no yaml dependency): a non-indented line ending
    in ``:`` opens a lemma block; an indented ``strongs: N`` line inside it
    yields a row. Lemmas with no ``strongs`` field are skipped (no bridge).
    """
    current_lemma: str | None = None
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            stripped = line.rstrip("\n")
            if not stripped.strip():
                continue
            if not stripped[0].isspace():
                # Top-level key: ``<lemma>:``
                if stripped.endswith(":"):
                    current_lemma = stripped[:-1].strip()
                else:
                    current_lemma = None
                continue
            # Indented property line.
            if current_lemma is None:
                continue
            body = stripped.strip()
            if body.startswith("strongs:"):
                raw_value = body[len("strongs:") :].strip()
                strongs = normalize_strongs(raw_value)
                if strongs is not None:
                    yield LemmaStrongs(
                        morphgnt_lemma=current_lemma, strongs=strongs
                    )


def parse_tbesg(path: Path) -> Iterator[StrongsGloss]:
    """Yield ``StrongsGloss`` rows (source='tbesg') from the TBESG txt file.

    Skips the prose header; a data row is a tab-split line whose first field
    normalizes to a Strong's number. Uses field 6 (short gloss) as the gloss
    and field 3 (unicode Greek) as the lemma. Rows whose first field is not a
    Strong's (header lines, the Proper-Noun ``Herod@...`` blocks) are skipped.
    """
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 7:
                continue
            strongs = normalize_strongs(parts[0])
            if strongs is None:
                continue
            lemma = parts[3].strip() or None
            gloss = parts[6].strip()
            if not gloss:
                continue
            yield StrongsGloss(
                strongs=strongs, lemma=lemma, gloss=gloss, source="tbesg"
            )


def parse_dodson(path: Path) -> Iterator[StrongsGloss]:
    """Yield ``StrongsGloss`` rows (source='dodson') from the Dodson tsv file.

    Tab-separated with a header row. Column 0 = Strong's (bare zero-padded),
    column 2 = Greek (beta code — kept as the lemma field for provenance only),
    column 3 = brief English definition (the gloss). The header row and any row
    whose column 0 is not a Strong's number are skipped.
    """
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        for row in reader:
            if len(row) < 4:
                continue
            strongs = normalize_strongs(row[0])
            if strongs is None:
                continue
            lemma = (row[2].strip() or None) if len(row) > 2 else None
            gloss = row[3].strip()
            if not gloss:
                continue
            yield StrongsGloss(
                strongs=strongs, lemma=lemma, gloss=gloss, source="dodson"
            )
