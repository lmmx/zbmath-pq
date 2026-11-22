# 2026-11-22: The zbMATH Open KG dump and the OAI-PMH source, measured

A reconnaissance, not an implementation: nothing in `src/` exists. The entry records
what the zbMATH Open knowledge graph dump contains, how it was built, what it drops
relative to its own source, and how much pre-1950 review text it holds. The design that
follows from it is `DESIGN.md` (a proposal). The census script and its small outputs are
in `2026-11-22-source-reconnaissance/`.

## Current State

- The KG dump is one file, `zbmath-kg-ttl-2026.tar.gz`, 1,621,106,686 bytes, md5
  `0846954acba8f9149a30cb91910d3c94`, in Zenodo record 21497976 (concept DOI
  10.5281/zenodo.21497975, published 2026-09-01) — the md5 of a full download made on
  2026-11-22 matches the record's.
- Zenodo's metadata gives the record's licence as `cc-by-4.0`, while the record's
  description and the zbmath-open-kg README give CC BY-SA 4.0 — the two statements
  disagree.
- The tarball holds one directory, `out-ttl-v2/`, of 11 Turtle members
  (`out-{1..8,401..404}-v2.ttl`, 0.20–1.74 GB each), 10,765,271,040 bytes decoded and
  184.4M triples in all (`members.parquet`, `log.txt`).
- Each member is one rdflib `Graph` serialised as Turtle by `create-rdf-v2.py`
  (zbMATHOpen/zbmath-open-kg `src/create-rdf-v2.py:166-423`) — every subject's triples
  form one contiguous block within a member, and zbl-id blank nodes are inlined as
  `[ ... ]` inside their document's block.
- Every document subject appears in exactly one member: 4,070,393 documents, none with a
  `dcterms:title` in two members (`census.py`, `log.txt`).
- Authors, keywords, MSC codes, journals, publishers and software appear as subjects in
  every member that mentions them — `subject_kinds.parquet` counts 2.73M author and
  4.82M keyword subject blocks across members, against the README's 1M+ persons and 3M+
  keywords.
- `create-rdf-v2.py` reads the OAI-PMH `oai_zb_preview` fields as JSONL and writes no
  triple for `source`, `spelling`, `time`, `rights`, reference strings (`text`) or
  `ref_classification` (`create-rdf-v2.py:166-411`; the field list is in
  `data/sample.jsonl`).
- `create-rdf-v2.py` attaches `dcterms:subject` (MSC) and `dcterms:creator` as unordered
  sets, so the primary MSC code (the first in `classification`) and the author order are
  absent from the KG.
- `create-rdf-v2.py` attaches each author's name to the author entity
  (`schema:name`), not to the authorship, so the name as printed on each document is
  absent from the KG.
- `create-rdf-v2.py` `make_id` builds keyword, journal, publisher and fallback-author
  IRIs by deleting every character outside `[A-Za-z0-9_]` (`create-rdf-v2.py:126-128`) —
  "Iséki" becomes `Iski`, so distinct non-ASCII labels can share one IRI.
- The census (`census.py`) streams the tarball through rapidgzip, `tarfile` in stream
  mode and pyoxigraph's lenient Turtle parser, with nothing written to disk, in 8m56s on
  this 4-core machine at 20–23 MB/s a member — the rate is bound by the Python loop per
  triple.
- pyoxigraph 0.5.13 parses the first 200 MB of `out-7-v2.ttl` at 75 MB/s (1.17M triples/s)
  on one core when the loop body only counts triples (`oxbench.py` in the session
  scratchpad; not kept).
- rapidgzip decodes the whole tarball in 13.9 s on 4 threads (41 s CPU); `gzip -dc`
  decodes the whole tarball in 55.3 s.
- 3,098,767 review subjects exist: 1,975,753 carry review text and 1,123,014 carry the
  placeholder "zbMATH Open Web Interface contents unavailable due to conflicting
  licenses." (`decades.csv`).
- 296,715 documents carry a publication year of 1949 or earlier; 171,552 of those carry
  review text, 169,363,074 characters in all (`decades.csv`).
- Pre-1950 review text is 96% German: 165,160 German, 6,241 English, 65 French
  (`census.py` output, session log).
- Pre-1950 documents by language: English 86,115, German 82,468, French 65,205, Italian
  29,530, Russian 9,458, Dutch 5,429 (`pre1950_languages.csv`); 1,726 pre-1950 documents
  carry the placeholder string as their language.
- 223,270 documents carry a JFM-style identifier (`vv.pppp.nn`), equal to the OAI-PMH
  `JFM` set's `completeListSize` of 223,270.
- JFM documents carry review text for 75–90% of documents in every decade from the 1870s
  to 1942; Zbl documents of 1931–1949 (Zbl volumes 1–59) carry review text for 47–1,091
  documents a year out of 2,077–4,691, about 3% before 1940 (`decades.csv`, session log).
- Documents published 1947–1979 carry review text for 1–4% a decade (`decades.csv`) — the
  share returns to 62% in the 1980s.
- Each JFM volume's documents have publication years within 2 years at the 5th–95th
  percentile (volume 1: 1867–1868; volume 54: 1928; volume 68: 1940–1942) — a review's
  JFM volume dates the review.
- Zbl volume 63 (median publication year of its documents about 1956) holds 5,488
  documents published 1864–1949, 5,220 of them with review text, including stubs of 12
  characters — reviews written in the 1950s of earlier papers.
- MSC codes are attached to 1,040–7,580 documents a decade before 1930 out of
  12,523–38,661, and keywords to 349–6,989 (`decades.csv`).
- `cito:cites` edges number 15,251,614 from 1,012,789 citing documents; 4,776 documents
  published before 1950 cite anything (`decades.csv`, `with_citations`).
- `oai.zbmath.org/v1/` answers OAI-PMH 2.0 `Identify`, `ListMetadataFormats` (`oai_dc`,
  `oai_zb_preview`), `ListSets` (MSC top-level classes and `JFM`), `GetRecord` and
  `ListRecords` without the API's terms page; a `ListRecords` page of set `JFM` returns
  100 records in 12.2 s (one request, 2026-11-22).
- The `oai_zb_preview` record of document 2577327 (Radó 1928, JFM `54.0517.02`) carries
  `source`, `spelling`, a German review with LaTeX, `links` and a `rights` statement:
  zbMATH Open content under CC BY-SA 4.0, bibliographic metadata and reference data
  derived from I4OC under CC0, third-party content replaced by the placeholder string.
- The first `ListRecords` page of set `JFM` (100 records, all 1900s) carries review text
  for 83 records, the placeholder for 4, median review length 803 characters, all German.
- `api.zbmath.org/v1/document/_search` returned HTTP 502 on 2026-11-22.
- A Zenodo search for "zbMATH scanned reviews", "zbMATH Mathpix", "Zentralblatt reviews
  OCR" and "zbMATH Open digitisation" returns no deposit of separated or OCR'd scanned
  reviews.

## Missing

- A deposit of the scanned Zbl reviews of volumes 1–529 (1932–1984) described in EMS
  Magazine 140 (doi 10.4171/mag/315): not located on Zenodo, and the article's full text
  was not read.
- Review publication dates: the OAI `datestamp` and `time` of JFM records read
  `0001-01-01T00:00:00`, and the KG carries neither.
- The census does not separate review stubs (texts of a few characters) from reviews.
