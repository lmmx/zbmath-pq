"""One streaming pass over the zbMATH KG tarball: per-document facts for the 'fuel' census.

Not pipeline code: a reconnaissance probe. tar.gz -> rapidgzip -> tarfile stream -> pyoxigraph
streaming Turtle parse, member by member; nothing extracted to disk.
"""
import sys, time, tarfile, collections
import rapidgzip, pyoxigraph as ox, polars as pl

PATH, OUT = sys.argv[1], sys.argv[2]
Z = "https://zbmath.org/"
S = "https://schema.org/"
D = "http://purl.org/dc/terms/"
PLACEHOLDER = "zbMATH Open Web Interface contents unavailable"

doc = collections.defaultdict(dict)       # doc id -> fields
rev = {}                                  # doc id -> (len, lang, placeholder)
pred_count = collections.Counter()
subj_kind = collections.Counter()
member_stats = []
seen_doc_files = collections.Counter()

def kind(iri: str) -> str:
    if iri.startswith(Z):
        rest = iri[len(Z):]
        head = rest.split("/", 1)[0]
        return "document" if head.isdigit() else head
    return iri.split("/")[2] if "://" in iri else "other"

t0 = time.time()
f = rapidgzip.open(PATH, parallelization=4)
import atexit; atexit.register(f.close)
tar = tarfile.open(fileobj=f, mode="r|")
for m in tar:
    if not m.isfile():
        continue
    tm, n, last_subj = time.time(), 0, None
    fh = tar.extractfile(m)
    for q in ox.parse(input=fh, format=ox.RdfFormat.TURTLE, lenient=True):
        n += 1
        s, p, o = q.subject, q.predicate.value, q.object
        pred_count[p] += 1
        sv = s.value if isinstance(s, ox.NamedNode) else "_:"
        if sv != last_subj:
            subj_kind[kind(sv) if sv != "_:" else "bnode"] += 1
            last_subj = sv
        if sv.startswith(Z) and sv[len(Z):].isdigit():
            d = doc[sv[len(Z):]]
            if p == D + "issued":
                d["year"] = o.value
            elif p == D + "language":
                d["lang"] = o.value
            elif p == D + "identifier":
                d["zbl"] = o.value
            elif p == "http://purl.org/spar/cito/cites":
                d["refs"] = d.get("refs", 0) + 1
            elif p == D + "creator":
                d["authors"] = d.get("authors", 0) + 1
            elif p == D + "subject":
                d["msc"] = d.get("msc", 0) + 1
            elif p == S + "keywords":
                d["kw"] = d.get("kw", 0) + 1
            elif p == D + "title":
                d["title_len"] = len(o.value)
                seen_doc_files[sv] += 1
        elif sv.startswith(Z + "review/"):
            did = sv[len(Z) + 7:]
            r = rev.setdefault(did, [0, None, False])
            if p == S + "reviewBody":
                r[0] = len(o.value)
                r[2] = o.value.startswith(PLACEHOLDER)
            elif p == S + "inLanguage":
                r[1] = o.value
    dt = time.time() - tm
    member_stats.append((m.name, m.size, n, dt))
    print(f"{m.name}: {m.size/1e9:.2f} GB, {n/1e6:.1f}M triples, {dt:.0f}s "
          f"({m.size/dt/1e6:.0f} MB/s); total {time.time()-t0:.0f}s", flush=True)

rows = []
for did, d in doc.items():
    r = rev.get(did)
    rows.append(dict(id=int(did), year=d.get("year"), lang=d.get("lang"), zbl=d.get("zbl"),
                     refs=d.get("refs", 0), authors=d.get("authors", 0), msc=d.get("msc", 0),
                     kw=d.get("kw", 0), has_title="title_len" in d,
                     review_len=r[0] if r else None, review_lang=r[1] if r else None,
                     review_placeholder=r[2] if r else None))
pl.DataFrame(rows, infer_schema_length=None).write_parquet(f"{OUT}/docs_census.parquet")
pl.DataFrame([dict(p=k, n=v) for k, v in pred_count.most_common()]).write_parquet(f"{OUT}/predicates.parquet")
pl.DataFrame([dict(kind=k, n=v) for k, v in subj_kind.most_common()]).write_parquet(f"{OUT}/subject_kinds.parquet")
pl.DataFrame(member_stats, schema=["member", "bytes", "triples", "secs"], orient="row").write_parquet(f"{OUT}/members.parquet")
dup = sum(1 for v in seen_doc_files.values() if v > 1)
print(f"done {time.time()-t0:.0f}s; docs={len(doc)} reviews={len(rev)} docs-with-title-in->1-file={dup}")
