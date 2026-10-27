# Hackathon window separation — read this first

This file is the single source of truth a judge needs to tell pre-existing work
apart from work done during the official **Oct 27 – Nov 4, 2026** build window
for the Meta Global AI Developer Hackathon (hosted with Cerebral Valley,
Startup track). It exists because Menivor (menivor.com) is an existing,
revenue-bearing product, not a from-scratch hackathon build, and the
hackathon's own rules require this separation or risk disqualification.

## The exact boundary

Tag **[`pre-hackathon-window`](../../tree/pre-hackathon-window)** marks the
commit at which this repo stood the moment the build window opened:

```
git log pre-hackathon-window..main      # every commit built inside the window
git diff pre-hackathon-window...main    # every line changed inside the window
```

As of this tag, this repo had exactly two commits, both dated **2026-10-26**
(before the Oct 27 window opened):

| Commit | Date | What |
|---|---|---|
| `9ff6edf` | 2026-10-26 22:48 +03 | Extraction of the Muse Image + SAM 3.1 provider adapters (written 2026-10-23, while evaluating Meta's Model API against Menivor's existing provider-routing architecture — **ahead of hackathon acceptance**, so it predates the window by definition) into this standalone, runnable, public repo. |
| `3883c0d` | 2026-10-26 23:12 +03 | `SUBMISSION.md` + `DEMO-SCRIPT.md` writeup. |

Everything at or before `pre-hackathon-window` is **pre-existing Menivor
infrastructure being reused**, not hackathon-original work:

- The two provider adapters (`app/domains/routing/providers/muse_image.py`,
  `sam_segment.py`) and the generic `ProviderAdapter`/`ProviderRegistry`
  contract they implement (`app/domains/routing/base.py`) — built 2026-10-23.
- The pytest suite for both adapters — copied verbatim from the private repo
  the same day.
- The fact that Menivor itself (menivor.com) exists at all — live since before
  this hackathon was announced.

## What's genuinely hackathon-window work (built Oct 27 – Nov 4)

Tracked here as it lands, each as its own commit *after* the
`pre-hackathon-window` tag so the `git log`/`git diff` commands above always
show the real, current window diff — no manual bookkeeping required beyond
keeping commits in this repo:

- The first real authenticated call against `api.meta.ai` using the owner's
  claimed `MODEL_API_KEY` (credits were claimed and the key went live
  2026-10-26, i.e. just before the window — the **first live call through
  this repo's own adapter code**, as opposed to the private production repo,
  still needs to happen inside the window and be committed here as evidence).
- Real before/after proof artifacts from that call (SAM 3.1 cutout + Muse
  Image generation), committed into this repo rather than left in `/tmp`.
- The 3-minute demo video recording itself (per `DEMO-SCRIPT.md`) and its
  published link.
- Any adapter bug fixes discovered while producing the above (e.g. the kind of
  SAM grounding-phrase issue already found and fixed in the private repo on
  2026-10-26 — if an equivalent fix is needed here, it lands as its own
  dated commit, not folded into the pre-window extraction).

## Why the production codebase isn't in this repo

Menivor's real codebase (`github.com/caelum0x/videogen`) is a private,
70-table-schema, real-billing monorepo going back months — publishing it
wholesale would be a one-way business-IP disclosure decision, not a
reversible packaging choice, so it stays private. This repo is a genuine,
runnable extraction of only the hackathon-relevant adapter code (see
`README.md` for exactly what was copied and why), kept current with the
private repo's own `pre-hackathon-window-2026-10-27` tag as the equivalent
boundary marker on that side.
