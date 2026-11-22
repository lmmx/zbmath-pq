fmt:
   ruff format src/zbmath scripts

# The gzip decoder backends (src/zbmath/decode.py; DESIGN.md, "Decisions") on crafted
# inputs: the same bytes as Python's gzip module, and truncated or corrupt streams rejected
test-decode:
   uv run --frozen python scripts/test_decode.py

# Every installed backend on a real gzip file (the KG tarball by default), which must
# agree on length and sha256. DECODERS narrows it, e.g. `just decoder-parity F rapidgzip,upigz`
decoder-parity path="releases/kg-2026/dump/zbmath-kg-ttl-2026.tar.gz" decoders="":
   uv run --frozen decoder-parity {{path}} {{ if decoders == "" { "" } else { "--decoders " + decoders } }}
