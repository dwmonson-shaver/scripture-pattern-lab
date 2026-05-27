"""Lexicon ingestion subpackage (Slice N, DEC-103).

Self-hosted open-lexicon stack for Tier-1 concept auto-generation. Parsers +
bulk loaders for the three datasets (jtauber lemma↔Strong's bridge, STEPBible
TBESG glosses, Dodson glosses). File IO + DB insert only — query-side packages
do not reach in here (DEC-025), and this package does not import them.
"""
