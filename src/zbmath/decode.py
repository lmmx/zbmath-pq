"""The gzip decoder backend: the KG tarball's bytes, decoded, as one readable stream.

The backend is chosen by ZBMATH_GZ_DECODER (DESIGN.md, "Decisions", 2026-11-22):

- `rapidgzip` (the default): decoded in this process, in parallel (rapidgzip's
  speculative block search), on GZ_THREADS threads;
- `upigz`: the user's decoder, once installed, as a subprocess, `upigz -dc`;
- `igzip`, `pigz`, `gzip`: subprocesses, as wikidata-pq's DECODERS["gz"].

Every backend is read the same way, so the stages after it do not depend on which one
decoded. `decoder-parity` checks that backends agree byte for byte.

From wikidata-pq src/wikidata/dump.py (DECODERS, bz2_threads and _dump_lines'
subprocess handling), adapted to gzip and a whole file; following a
download still being written (`_feed`) comes with the downloader.
"""

import argparse
import hashlib
import io
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from . import config

# The in-process backends, and the subprocess ones' commands (the path is appended)
IN_PROCESS = ("rapidgzip",)
SUBPROCESS = {
    "upigz": ["upigz", "-dc"],
    "igzip": ["igzip", "-dc"],
    "pigz": ["pigz", "-dc"],
    "gzip": ["gzip", "-dc"],
}
DECODERS = (*IN_PROCESS, *SUBPROCESS)
READ_BYTES = 16 << 20


def gz_threads() -> int:
    """A parallel decoder's threads (ZBMATH_GZ_THREADS, by default 1: see config)."""
    return config.GZ_THREADS


def available(name: str) -> bool:
    """Whether the backend `name` can run here."""
    if name == "rapidgzip":
        try:
            import rapidgzip  # noqa: F401
        except ImportError:
            return False
        return True
    return shutil.which(SUBPROCESS[name][0]) is not None


def check_name(name: str) -> str:
    if name not in DECODERS:
        raise SystemExit(f"ZBMATH_GZ_DECODER is one of {', '.join(DECODERS)}, not {name!r}")
    if not available(name):
        raise SystemExit(f"the gzip decoder {name!r} is not installed")
    return name


class _Consumed(io.RawIOBase):
    """rapidgzip's output, raising at its end unless the decode consumed every bit of the
    input. rapidgzip 0.16.2 ends a stream truncated inside a deflate block without an
    error, returning the bytes decoded so far (it raises on a missing footer, a bad CRC32
    or size, or a corrupt block); its compressed position then stops short of the file's
    end (docs/journal/2026-11-22-gzip-decoder-backend.md)."""

    def __init__(self, f, bits: int):
        self.f, self.bits = f, bits

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        n = self.f.readinto(buffer)
        if not n and len(buffer) and (at := self.f.tell_compressed()) != self.bits:
            raise RuntimeError(f"rapidgzip: the stream ended at bit {at} of {self.bits} "
                               "(a truncated or trailing-garbage gzip file)")
        return n


@contextmanager
def decoded(path: Path, name: str | None = None) -> Iterator[BinaryIO]:
    """The gzip file at `path`, decoded by the backend `name` (ZBMATH_GZ_DECODER by
    default), as a readable binary stream. A corrupt or truncated stream raises, from the
    read that reaches it or on leaving the context (a subprocess's exit status); leaving
    early, before the end, does not."""
    name = check_name(name or config.GZ_DECODER)
    if name == "rapidgzip":
        import rapidgzip

        f = rapidgzip.open(str(path), parallelization=gz_threads())
        try:
            yield _Consumed(f, path.stat().st_size * 8)
        finally:
            f.close()
        return
    proc = subprocess.Popen([*SUBPROCESS[name], str(path)], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, bufsize=READ_BYTES)
    early = False
    try:
        yield proc.stdout
    except GeneratorExit:
        early = True
        raise
    finally:
        proc.stdout.close()
        code = proc.wait()
        err = proc.stderr.read().decode(errors="replace").strip()
        proc.stderr.close()
        if code not in (0, -13) and not early:  # -13: closed early (SIGPIPE)
            raise RuntimeError(f"{name} exited with {code}: {err}")


def digest(path: Path, name: str) -> tuple[int, str, float]:
    """The decoded length and sha256 of `path` by the backend `name`, and the seconds the
    decode and the hash took together."""
    h, n, t = hashlib.sha256(), 0, time.perf_counter()
    with decoded(path, name) as f:
        while block := f.read(READ_BYTES):
            h.update(block)
            n += len(block)
    return n, h.hexdigest(), time.perf_counter() - t


def run_parity(argv: list[str] | None = None) -> None:
    """decoder-parity PATH [--decoders a,b,...]: decode PATH with each backend (every
    installed one by default) and fail unless all agree on length and sha256."""
    p = argparse.ArgumentParser(prog="decoder-parity")
    p.add_argument("path", type=Path)
    p.add_argument("--decoders", default=",".join(DECODERS))
    a = p.parse_args(argv)
    names = [n for n in a.decoders.split(",") if n]
    for n in names:
        if n not in DECODERS:
            raise SystemExit(f"unknown decoder {n!r}: one of {', '.join(DECODERS)}")
    names = [n for n in names if available(n) or print(f"{n}: not installed, skipped")]
    if len(names) < 2:
        raise SystemExit("parity needs two installed decoders")
    results = {}
    for n in names:
        size, sha, secs = digest(a.path, n)
        results[n] = (size, sha)
        threads = f", {gz_threads()} threads" if n == "rapidgzip" else ""
        print(f"{n}{threads}: {size} bytes, sha256 {sha}, {secs:.1f} s (decode and hash)",
              flush=True)
    if len(set(results.values())) != 1:
        raise SystemExit("parity FAILED: the decoders disagree")
    print(f"parity: {len(names)} decoders agree")


if __name__ == "__main__":
    run_parity(sys.argv[1:])
