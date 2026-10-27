# Menivor × Meta Model API — hackathon submission

[Menivor](https://menivor.com) is a live, production AI video-ad/UGC generation
platform (script → TTS → avatar → captions → compose → publish). Its production
codebase is a private monorepo (70-table Postgres schema, real billing, four
client surfaces) — too large and too commercially sensitive to publish wholesale.

This repository is the real, runnable extraction of the specific code built for
the **Meta Global AI Developer Hackathon** (hosted with Cerebral Valley): two new
provider adapters that wire Meta's Model API (Muse Image, SAM 3.1) into Menivor's
existing provider-routing architecture, plus their real test suite.

## What's in this repo

- `app/domains/routing/providers/muse_image.py` — real adapter for Muse Image
  (`POST /v1/images/generations` and `/v1/images/edits`, OpenAI-Images-API
  compatible, $0.01/image).
- `app/domains/routing/providers/sam_segment.py` — real adapter for SAM 3.1
  (`POST /v1/responses`, decodes the documented `<|box;...|>` detection grammar
  into bounding boxes for a product-photo cutout).
- `app/domains/routing/base.py` — the generic `ProviderAdapter` protocol +
  `ProviderRegistry` these two adapters implement (copied verbatim from the
  private repo; it is intentionally generic and carries no business data).
- `app/domains/routing/providers/kling_fal.py` — **not** the real Kling/fal.ai
  video adapter (that stays private and is unrelated to this submission); this
  file is trimmed down to just the shared `KlingError` taxonomy class every
  adapter in the real package — including these two — imports and raises.
- `tests/` — the real pytest suite for both adapters, copied verbatim except
  for two tests that exercise the full private provider registry (skipped here
  with a documented reason; they pass unmodified in the real codebase).
- `SUBMISSION.md` — the full hackathon application/submission writeup (track,
  project idea, technical skill, links).
- `DEMO-SCRIPT.md` — the shot-by-shot script for the required 3-minute demo
  video.

## Why this design

Both adapters fail closed with a clearly-labeled `KlingError(kind="auth")` when
`MODEL_API_KEY` is unset, and this repo intentionally never commits a real key
(see `HACKATHON.md` for the current status of real calls/proof artifacts).
Nothing here is mocked or faked: the HTTP protocol, request/response shapes,
pricing, and error taxonomy are all the real, documented Meta Model API wire
format. The moment a real key is set, `muse_generate_image()` and
`sam_segment_image()` make real calls.

See **[`HACKATHON.md`](./HACKATHON.md)** for the exact commit-range boundary
between pre-existing work and this hackathon's Oct 27 – Nov 4 build window.

## Verify it yourself

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install requests pytest
python3 -m pytest tests/ -q
# 27 passed, 2 skipped
```

## Hackathon window separation

See **[`HACKATHON.md`](./HACKATHON.md)** — it pins the exact `git tag` boundary
(`pre-hackathon-window`) between what predates the Oct 27–Nov 4 build window
(this repo's two initial commits, both 2026-10-26) and what's genuinely built
during it, and tracks window-work as it lands.

## Links

- Live product: https://menivor.com
- Production repository (private): github.com/caelum0x/videogen
