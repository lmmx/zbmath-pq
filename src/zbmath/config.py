"""Configuration constants for the zbMATH pipeline (every knob an environment variable,
as in wikidata-pq's config.py)."""

import os
from pathlib import Path

# The KG dump (DESIGN.md, "The source, as measured"): Zenodo record 21497976, concept DOI
# 10.5281/zenodo.21497975
KG_RELEASE = os.environ.get("ZBMATH_KG_RELEASE") or "kg-2026"
KG_ARCHIVE = "zbmath-kg-ttl-2026.tar.gz"
RELEASES_DIR = Path("releases")
WORK_DIR = RELEASES_DIR / KG_RELEASE
DUMP_DIR = WORK_DIR / "dump"

# The gzip decoder (DESIGN.md, "Decisions", 2026-11-22; src/zbmath/decode.py)
GZ_DECODER = os.environ.get("ZBMATH_GZ_DECODER") or "rapidgzip"
# Its threads, where it decodes in parallel: by default 1. On the KG tarball rapidgzip
# decodes in 12.8 s on 1 thread (12.8 CPU s), 19.5 s on 2 (38.4 CPU s) and 10.8 s on 4
# (38.2 CPU s): its sequential path is 3 times cheaper than its parallel one, and the
# cores are the parse workers' (docs/journal/2026-11-22-gzip-decoder-backend.md)
GZ_THREADS = int(os.environ.get("ZBMATH_GZ_THREADS") or 1)
