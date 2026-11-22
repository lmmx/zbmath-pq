# zbmath-pq design

**Status: proposal, 2026-11-22, for the user's review.** Nothing below is implemented.
The evidence is in `docs/journal/2026-11-22-source-reconnaissance.md`. Decisions the
user makes are recorded under "Decisions" and are not reopened without a new reason.

## Purpose

zbmath-pq turns zbMATH Open's record of mathematics (4.07M documents, 1763–2026) into
typed Parquet tables that can be downloaded and queried a slice at a time — a period, a
field, a language — without a triple store, a SPARQL endpoint or the zbMATH API. It is a
dataset pipeline in the manner of lmmx/wikidata-pq, and a complete product on its own.
A retrieval layer built on it (capability descriptions, embeddings) is a later and
separate stage, in its own directory or repository, reading the published tables.

## The source, as measured

- **The KG dump** (Zenodo 10.5281/zenodo.21497975, version record 21497976): one
  `zbmath-kg-ttl-2026.tar.gz`, 1,621,106,686 bytes, md5 `0846954acba8f9149a30cb91910d3c94`;
  11 Turtle members (`out-ttl-v2/out-{1..8,401..404}-v2.ttl`), 10.77 GB decoded, 184.4M
  triples. Each member is one rdflib graph serialised by `create-rdf-v2.py`
  (zbMATHOpen/zbmath-open-kg): every subject's triples form one contiguous block, every
  document lives in exactly one member, and the shared entities (authors, keywords, MSC
  codes, journals, publishers, software) recur in every member that mentions them.
- **The KG is derived and lossy.** It was built from the OAI-PMH `oai_zb_preview` records
  (JSONL), and drops: `source` (the citation string, e.g. "C. R. 186, 346-348 (1928)."),
  `spelling` (name variants), `time`, `rights`, reference strings (`text`) and
  `ref_classification`; the order of `classification` (so the primary MSC code) and of
  authors; and each authorship's printed name (names hang on the author entity). Keyword,
  journal and publisher IRIs are made by deleting every character outside `[A-Za-z0-9_]`,
  so distinct non-ASCII keywords can share one IRI.
- **The primary source** is `oai.zbmath.org/v1/` (OAI-PMH 2.0, `oai_zb_preview`), open
  without the API's terms page, 100 records a page, about 12 s a page measured, with sets
  per MSC top-level class and `JFM` (223,270 records). Its `rights` field: zbMATH Open
  content (reviews, classifications, author disambiguation, software) CC BY-SA 4.0;
  bibliographic and reference data CC0; third-party text withheld as the placeholder
  "zbMATH Open Web Interface contents unavailable due to conflicting licenses."
- **The pre-1950 fuel:** 296,715 documents; 171,552 with review text, 169M characters,
  96% of it German. JFM (1868–1942) has text for 75–90% of documents in every decade. Zbl
  volumes 1–59 (documents of 1931–1949) have text for about 3%; the gap runs to about 1980
  and is the scanned-review backlog. MSC codes and keywords are sparse before 1930;
  citations (`cito:cites`) are nearly absent before 1950 (4,776 documents) — the review
  text is the historical record's only semantic content.

## Architecture

### The principle carried over

wikidata-pq's method (`docs/journal/2026-10-25-architecture-trace.md` there): trace every
intermediate and ask what information forces it to exist. Keep the ones that are real —
a restart point, a global operation, the published contract — and remove the historical
ones. At this source's size the answer differs from Wikidata's, and the design says so
rather than importing machinery whose reason does not hold here:

| intermediate | forced? | here |
|---|---|---|
| the tarball on disk | yes: download restart point, md5 | kept (1.6 GB) |
| decoded Turtle (10.8 GB) | no | never materialised; held in memory, bounded |
| per-chunk part files | in wikidata-pq: an 8 h run's restart points and out-of-order workers | **not** for the dump: the whole conversion is about 2 minutes of compute (below), so a crash reruns it; outputs are written `.tmp` and renamed |
| cross-member entity merge | yes: an author or keyword recurs in every member | in memory (≤ 5M rows a table); no bucket sort |
| global sort | yes: the published order | in memory (the largest table, reviews, ~2 GB of text) |
| the OAI page log | yes: a multi-day harvest's restart point | kept: the analogue of the `.part` and the split's manifest |

### Two source adapters, one record model

The record model is the OAI `oai_zb_preview` field set, since the KG is a projection of
it. Each adapter emits the same Arrow tables, with null where its source lacks a field
and a `source` provenance column (`kg-2026` or `oai-YYYY-MM-DD`).

1. **`kg`, the Zenodo dump** (first). `download` (wikidata-pq's resumable range
   downloader and its md5 check, the checksum from the Zenodo API) → `rapidgzip`
   (parallel gzip; 14 s for the whole tarball on 4 cores, against 55 s for `gzip`) →
   `tarfile` in stream mode → a chunker cutting each member at subject-block boundaries
   (a blank line outside a `"""` literal), each chunk carrying the member's `@prefix`
   header → a pool of threads running the Rust kernel → Arrow → Parquet.
2. **`oai`, the harvest** (second, beginning with set `JFM`). Pages are appended to a
   zstd page log with the resumption token beside each page (the restart point), and
   conversion follows the log as it grows, as wikidata-pq's split follows the download.
   Later releases harvest incrementally with `from=`. This adapter restores everything
   the KG drops.

### The Rust kernel (`reshape/`, as in wikidata-pq)

A pyo3 crate parsing Turtle with `oxttl` (the parser under pyoxigraph: 75 MB/s a core
measured through the Python binding, 22 MB/s with a Python loop per triple) straight into
Arrow builders, one per table, releasing the GIL, returning Arrow through the C data
interface. Subject IRIs dispatch by prefix (`zbmath:<digits>` document, `review/`,
`authors/`, `keyword/`, `msc2020.org`, ...). Per-member entity rows are deduplicated by
IRI in the kernel; across members in Polars. A chunk the kernel cannot read falls back to
a Python reference path built on pyoxigraph, which also defines the kernel's expected
output for the parity tests (wikidata-pq's "fast path, checked fallback").

Expected compute, modelled from the measured rates: about 10.8 GB ÷ (75 MB/s × 4 cores)
≈ 40 s of parsing beside 14 s of decoding on 4 cores — about a minute or two end to end
against the census's 9 minutes in Python.

### Tables

| table | rows (KG) | key | content |
|---|---:|---|---|
| `documents` | 4,070,393 | `id` | zbl_id, origin (`jfm`/`zbl`), year, language, title, doc_type, pagination, journal_id, publisher_ids, doi, urls, msc (list), keywords (list of labels), author_ids (list), software_ids (list) |
| `reviews` | 3,098,767 | `document_id` | text (null where withheld), withheld (bool), language, review_type, reviewer_id, reviewer_name, review_volume, review_year_est |
| `citations` | 15,251,614 | (`citing_id`, `cited_id`) | the `cito:cites` edges |
| `authors` | ~1M | `id` | names (list) |
| `keywords` | — | label | the label as printed (not the stripped IRI), document count |
| `msc` | 6.7K | `code` | label, parent |
| `journals`, `publishers`, `software` | 41K, 22K, 84K occurrences | `id` | name |

**Publication year and review year are separate columns.** `review_volume` comes from
the identifier (JFM `54.0517.02` → volume 54; Zbl `0063.00215` → volume 63) and
`review_year_est` from each volume's median publication year, measured: JFM volumes span
2 years at most (5th–95th percentile), so the estimate is tight there. A review in a
later Zbl volume of an earlier paper (volume 63, about 1956, holds 5,488 documents of
1864–1949) is visible as such and can be excluded from a strictly historical slice.

### Layout and subsets

The whole dataset is a few GB of Parquet (reviews the largest), so wikidata-pq's
reason for splitting by language (a terabyte) does not apply. The proposal: each table
sorted by (`year`, `id`) with `sorting_columns` declared and row groups small enough that
a decade is a handful of row groups, plus Hub configs over era file globs (e.g.
`historical`: year ≤ 1949). Splitting further by MSC class is weak before 1930, where most
documents have no MSC code. The layout is the user's decision (open question 2).

### Checks (from wikidata-pq, kept exact)

- id preservation per table against the source's subject counts;
- row counts against the kernel's per-chunk census, merged at the end;
- the kernel against the Python reference path on a fixed sample (parity);
- sort checks as `sort_by_id._check_sort` and `_check_written`;
- the published files by size and sha256 after an approved upload.

### Reuse of wikidata-pq

Mechanisms carried over as code or as patterns: the resumable downloader and
follow-the-file feeder (`dump.py` `download`, `_feed`); the bounded, ordered split loop
(`MAX_PENDING_BYTES`, the in-order manifest); the `reshape` crate pattern (GIL release,
zero-copy buffers, checked fallback, `partition.rs`'s minimal Parquet writer for flat
tables); `.tmp` and rename plus append-only JSONL ledgers; `schema_evolution.py` for the
OAI adapter's open field set; the sort checks; `cards.py`'s rendering from computed
stats; `hub.py`'s build-branch-and-promote. Not carried over, because their reason does
not hold at this size or format: groups and group closing, compaction, the bucketed
external sort, cross-run finalise, the scholarly routing, the bz2 decoder. How the shared
code is shared (copied, or extracted into a package both repositories use) is open
question 3.

## Justfile (proposed)

```
just download            # the KG tarball, resumable, md5-checked
just build               # tarball -> releases/kg-2026/{table}/*.parquet (local)
just check               # parity, counts, sort checks on the built tables
just harvest SET         # OAI-PMH into the page log, resumable (JFM first)
just build-oai SET       # the page log -> tables, following the harvest
just cards               # dataset cards from computed stats
just publish             # Hub upload: only with the user's go-ahead
```

## Open questions for the user

1. The source: the KG dump alone, or the OAI harvest as the eventual primary, given what
   the KG drops and the harvest's cost (about 7.5 h for JFM, days for everything at the
   measured page rate).
2. The published layout and its subsets.
3. How wikidata-pq's code is shared.
4. Publishing review text (CC BY-SA 4.0, attribution) in the first release, or the
   metadata tables first.

## Decisions

(none yet)
