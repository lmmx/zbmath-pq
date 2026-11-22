# 2026-11-22: The gzip decoder backend, its parity check, and rapidgzip on the KG tarball

The `kg` adapter's decode stage (DESIGN.md, "Decisions", 2026-11-22): a backend chosen by
`ZBMATH_GZ_DECODER`, read the same way whichever backend decodes, with byte parity
between backends checked, so that the user's decoder (working name upigz) replaces
rapidgzip without touching the stages after it. Measured on the session's machine: 4
cores of an Intel Xeon at 2.1 GHz with AVX-512, BMI2 and SHA-NI, no SMT, shared, so
indicative only. The scratch timing script is in `2026-11-22-gzip-decoder-backend/`.

## Current State

- `src/zbmath/decode.py` `decoded(path, name)` yields the decoded bytes of a gzip file as
  one readable stream: rapidgzip in process (`IN_PROCESS`), or `upigz`, `igzip`, `pigz` or
  `gzip` as a subprocess given `-dc PATH` (`SUBPROCESS`, from wikidata-pq
  `dump.DECODERS["gz"]`), chosen by `ZBMATH_GZ_DECODER` (default `rapidgzip`,
  `config.GZ_DECODER`).
- `decoded` raises for a subprocess that exits other than 0 or by SIGPIPE, unless the
  caller left the stream before its end (wikidata-pq `_dump_lines`' handling).
- rapidgzip 0.16.2 returns the bytes decoded so far, without raising, for a gzip stream
  truncated inside a deflate block (a 12,778,804-byte stream cut at half: 14,390,677 of
  28,888,890 bytes returned, a warning on stderr only) — rapidgzip raises for a missing
  footer, a mismatched CRC32, a mismatched size and a flipped byte mid-stream, with 1 or
  4 threads alike.
- rapidgzip's `tell_compressed()` at the end of a stream equals the file's size in bits
  after a whole decode (102,230,432 of 102,230,432) and falls short after a truncated one
  (50,953,350 of 51,115,216) — `decode._Consumed` raises at the end of rapidgzip's output
  unless `tell_compressed()` equals the file's size in bits.
- `scripts/test_decode.py` (`just test-decode`) checks every installed backend against
  Python's `gzip.decompress` on one member (23.8 MB), three concatenated members of
  levels 1, 9 and 6 (34.9 MB), an empty member and a tar.gz (27.0 MB), and checks that
  every installed backend raises on a truncated stream and on a corrupted CRC32 —
  rapidgzip (with 1 and with 4 threads) and gzip pass every case.
- `decoder-parity` (`just decoder-parity`) decodes a file with every installed backend
  and fails unless all agree on length and sha256 — on `zbmath-kg-ttl-2026.tar.gz`,
  rapidgzip and gzip 1.12 agree: 10,765,271,040 bytes, sha256
  `6f0781f6675cccd3edf74276ad2998a453df1d2e41fcc8d69308774fc08f07be`.
- rapidgzip in process, reading 16 MiB at a time into one buffer and nothing else
  (`dec_only.py`), decodes `zbmath-kg-ttl-2026.tar.gz` in 12.8 s wall and 12.8 s CPU on
  1 thread, 19.5 s wall and 38.4 s CPU on 2 threads, and 10.8 s wall and 38.2 s CPU on 4
  threads (10.5 s wall and 37.3 s CPU reading 1 MiB at a time).
- rapidgzip on 1 thread decodes 841 MB of output a second: about 2.5 cycles a decoded
  byte and 16.6 cycles a compressed byte at the nominal 2.1 GHz.
- `rapidgzip -d -c -P 4` piped to `wc -c` decodes the tarball in 13.9 s wall and 41.1 s
  user CPU; `gzip -dc` piped to `wc -c` decodes the tarball in 55.3 s wall
  (2026-11-22-source-reconnaissance.md).
- `decoder-parity` with sha256 in the reading thread takes 58.9 s for rapidgzip on 4
  threads and 27.1 s on 1 thread, against 10.8 s and 12.8 s without the hash — the
  1.24 GB/s sha256 runs in the same process as the decoder's threads, so parity timings
  are not decode timings.
- `config.GZ_THREADS` defaults to 1 (`ZBMATH_GZ_THREADS`) — the decode shares the
  machine's cores with the parse workers, and rapidgzip's parallel path spends 3 times
  the CPU of its sequential path for 16% less wall time on 4 threads.

## Missing

- `igzip`, `pigz` and libdeflate are not installed on the session's machine (no apt
  candidate for `pigz` or `isal`) — no measurement of them on the tarball exists.
- The decode stage does not yet follow a download still being written (wikidata-pq
  `dump._feed`); `decoded` reads a whole file.
- No `upigz` binary exists to put through `decoder-parity`.
