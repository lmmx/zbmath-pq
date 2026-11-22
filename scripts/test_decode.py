"""The gzip decoder backends (src/zbmath/decode.py) on small crafted inputs: each installed
backend gives the same bytes as Python's gzip module for one member, several concatenated
members, an empty member and a tar.gz; and each fails on a truncated stream and on a
corrupted CRC.

    .venv/bin/python scripts/test_decode.py
"""

import gzip
import io
import os
import random
import tarfile
import tempfile
from pathlib import Path

from zbmath import decode


def cases() -> dict[str, bytes]:
    rng = random.Random(0)
    text = b"".join(
        b"<https://zbmath.org/%d> a schema:ScholarlyArticle ;\n    dcterms:title \"%s\" .\n\n"
        % (i, bytes(rng.choice(b"abcdefgh \\\"") for _ in range(rng.randrange(80))))
        for i in range(200_000)
    )
    noise = rng.randbytes(3 << 20)
    tar = io.BytesIO()
    with tarfile.open(fileobj=tar, mode="w") as t:
        for name, data in (("out-ttl-v2/out-1-v2.ttl", text), ("out-ttl-v2/noise", noise)):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return {
        "one member": gzip.compress(text, 6),
        "concatenated members": gzip.compress(text[: len(text) // 3], 1)
        + gzip.compress(noise, 9)
        + gzip.compress(text, 6),
        "empty member": gzip.compress(b""),
        "tar.gz": gzip.compress(tar.getvalue(), 6),
    }


def decodes(path: Path, name: str) -> bytes:
    with decode.decoded(path, name) as f:
        return f.read()


def fails(path: Path, name: str) -> bool:
    try:
        decodes(path, name)
    except Exception:
        return True
    return False


def main() -> None:
    names = [n for n in decode.DECODERS if decode.available(n)]
    print("backends:", ", ".join(names))
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for label, gz in cases().items():
            p = d / "case.gz"
            p.write_bytes(gz)
            want = gzip.decompress(gz)
            for n in names:
                got = decodes(p, n)
                assert got == want, f"{n}, {label}: {len(got)} bytes, want {len(want)}"
            print(f"ok: {label} ({len(want)} bytes) by every backend")
        good = cases()["one member"]
        bad = {
            "truncated": good[: len(good) // 2],
            "corrupted CRC": good[:-8] + bytes(b ^ 0xFF for b in good[-8:-4]) + good[-4:],
        }
        for label, gz in bad.items():
            p = d / "bad.gz"
            p.write_bytes(gz)
            for n in names:
                assert fails(p, n), f"{n} accepted a {label} stream"
            print(f"ok: {label} stream rejected by every backend")
    print("test_decode: all passed")


if __name__ == "__main__":
    os.environ.setdefault("ZBMATH_GZ_THREADS", "4")  # (the parallel path, not the default)
    main()
