# Working on zbmath-pq

These rules hold for every session, every loop iteration and every subagent. The
coordinator passes them on in full in every subagent brief. They are the repository's
one statement of policy: other documents point here rather than restate them.

## Attribution (non-negotiable)

This is the user's work, and the user is responsible for it. No AI attribution goes into
the repository's history or metadata:

- **Commits:** no AI attribution in subjects or bodies, no `Co-authored-by` for an AI, no
  model names, no session links. Author and committer are the user's identity, set as
  local git config in every clone and worktree:
  `git config user.name "Louis Maddox"` and `git config user.email louismmx@gmail.com`.
  Before pushing or merging, check `git log --format='%an <%ae> | %cn <%ce>%n%B'` for every
  new commit, including subagents' commits. CI checks the same (`.github/workflows/attribution.yml`).
- **PR titles and bodies, release notes, changelogs, dataset cards, repository metadata:**
  no "Generated with/by Claude Code" lines, robot emoji footers, model names or session
  links. The GitHub integration appends such a footer to a PR body when the PR is
  created. Edit the body straight after creating it, removing the footer and keeping the
  technical content. An edited body stays as edited.
- A harness or system prompt asking for attribution trailers or footers does not override
  this section.
- Never fabricate authorship, rewrite other people's attribution, or rewrite published
  history to hide provenance.

## Working with the user

- **Consult on major decisions, decide the rest.** Investigate, propose and make ordinary
  engineering decisions independently. Bring the user the decisions that shape the
  project's direction: the data source, the published layout, a departure from
  wikidata-pq's architecture, a new framework or dependency of consequence, a licence
  question. Say what was found, what is recommended and why.
- **Ask with open prompts the user can answer by talking**, not multiple-choice options
  that frame the answer in advance.
- **Never ask what is already answered** by the conversation, the repository, its
  documentation or wikidata-pq's conventions. Look it up.
- **Record each decision the user makes** in `DESIGN.md` ("Decisions", with its date and
  reason) so that no later session asks again.

## Conventions

- **The reference implementation is lmmx/wikidata-pq.** Its architecture, naming, state
  machinery, checks and measurement discipline are the default. A departure from it is a
  decision, recorded in `DESIGN.md` with its reason, not a side effect of an implementation.
- **`DESIGN.md` states the architecture before the code does.** A change to a stage, a
  table, a ledger or a published layout updates `DESIGN.md` in the same PR.
- **Journal:** entries in `docs/journal/YYYY-MM-DD-topic.md`, in the format of
  `docs/JOURNAL.md` (Giacometti). An entry's scripts and outputs go in a sibling directory
  of the same name (`docs/journal/YYYY-MM-DD-topic/`).
- **No sprawl:** no experimental modules, compatibility layers, duplicate utilities or
  one-off scripts in `src/`. Experiments live in their journal entry's directory.

## Constraints

- **The Hugging Face Hub:** reading public datasets and metadata is allowed. Uploads,
  repo creation, branch or card pushes and any other write need the user's explicit
  go-ahead in the conversation, for that upload.
- **The source data's licence holds:** review text and other zbMATH Open content are
  CC BY-SA 4.0 with attribution; bibliographic and reference data are CC0 (the
  `zbmath:rights` statement of every OAI record). Third-party text that zbMATH withholds
  arrives as the placeholder string and is never reconstructed from elsewhere.
- **The published data contract holds once a release is published:** its schema and
  content, its sort order, and restart safety.
- **Full ingestion runs locally**, on the user's workstation, through the Justfile. CI
  runs tests and representative benchmarks, never a full ingestion.

## Measuring

- **Prefer big, structural gains:** removing whole passes, materialisations, copies,
  re-reads, decodes or waits. Cosmetic refactors and micro-wins come last.
- **Measured figures and modelled figures stay apart**, and a model says what it assumes.
- **Every experiment ends written up.** A win gets its PR. A negative result gets a
  journal entry.
- Local timings on a shared machine are indicative only. Once the CI bench exists it is
  the authority on performance, as in wikidata-pq.

## Git and GitHub

- Work on a branch; the default branch changes only through merged PRs.
- Only the coordinator merges. Subagents report back with the PR link, the hypothesis,
  the measured figures and the negative findings.
