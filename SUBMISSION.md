# Meta Global AI Developer Hackathon — application draft (Menivor)

Source: Cerebral Valley, https://cerebralvalley.ai/e/meta-ai-developer-hackathon
Application deadline: 2026-10-25 11:59pm ET (rolling, apply now). Build window if accepted: 2026-10-26 to 2026-11-04.

## 2026-10-23 update: the real integration is now built, and three claims below were corrected

Meta's Model API docs are public (not hackathon-gated) at `dev.meta.ai` — confirmed by
fetching them directly. That let the Muse Image and SAM 3.1 adapters below be built as
**real, wired infrastructure today**, not left as a plan:

* **Base URL / auth / env var**: `https://api.meta.ai/v1`, `Authorization: Bearer`, and
  Meta's own documented env var is **`MODEL_API_KEY`** (one key for every Model API
  service), not `MUSE_API_KEY`/`SAM_API_KEY` as originally assumed below — both adapters
  accept `MODEL_API_KEY` first and the per-product name as a fallback override.
* **Muse Wonder/Spark are not image/video generation models.** They are Meta's agentic
  coding/text models (1M-token context, OpenAI/Anthropic-SDK-compatible chat/Responses
  API) — the same family as Muse Code. The line below describing "Muse Image/Spark/Wonder
  (generative image/video)" overstated this: only **Muse Image** (`muse-image-1.0`)
  generates/edits images (`POST /v1/images/generations`, `/v1/images/edits`, OpenAI
  Images-API compatible, confirmed flat **$0.01/image**, 2026-08-28 Meta for Developers
  announcement). **There is no Muse video-generation model** — the "Spark/Wonder ...
  video" framing was wrong; this entry does not build a `muse_video.py`.
* **SAM 3.1 is real and hosted**: `POST /v1/responses` with `model: "sam-3.1"`, a
  short noun-phrase + an image/video input, returning detections as a documented
  special-token grammar (`<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|>` + a `<|mask;...|>`
  raster). Meta ships an official **JavaScript** raster decoder (`@meta-sam/parser`);
  there is no published Python decoder and the exact bit-packing of the mask's `data=`
  field isn't pinned down publicly, so the real adapter built here decodes the fully
  documented box grammar and uses a bounding-box cutout today, with pixel-exact raster
  decoding tracked as a follow-up once it runs against a live key.

**What's actually live in the repo now** (real code, not a plan): `app/domains/routing/providers/muse_image.py`
and `sam_segment.py` (same `KlingError` taxonomy, same retry/backoff as `kling_fal.py`),
wired into `media_catalog.py` (`meta/muse-image-1.0` + `-edit` rows, $0.01/image),
`gateway/provider_execution.py`'s `_submit_image` dispatch, `routing/license_class.py`
(`meta_model_api`, commercial-API, paid-safe), and `routing/providers/registry.py`'s
BYOK registry — all fail-closed on `MODEL_API_KEY` (unset today) exactly like every
other adapter. SAM 3.1 is wired as an optional, gated product-photo cutout refinement in
`adstudio/images.py` (crops to the detected product box before the existing Pillow
flatten) and as a new `adclone/vision.py` helper (`segment_subject`, same
"optional/lazy, degrades to None" contract as the OCR/face-framing helpers already
there). 38 new tests cover both adapters, the registry gating, and the cutout behavior
(default path byte-identical to before); the full `tests/reelforge` + `apps/api/tests`
suite was re-run green after the change. `adclone/engines.py`'s video-engine comparison
table was deliberately left untouched — it compares talking-head *video* engines
(Kling/Higgsfield/Replicate/Runpod/Hailuo), and Muse Image is a synchronous image model,
not a video engine, so adding it there would have been a forced fit. Similarly,
`adstudio/render.py`/`variants.py` (named below) are local-FFmpeg compositing with no
provider call at all; the real "Muse Image becomes selectable" surface is the media
catalog + gateway dispatch above, which is what any future Ad Studio/Ad Clone caller
would route a `meta/muse-image-1.0` request through.

## Why Menivor replaces Scribase for this entry

Scribase (`/Users/arhansubasi/products/supabase-plus-clone`) is backend infra — Postgres/auth/storage/deploy for agents and app teams. It has no real surface for Muse Image/Spark/Wonder (generative image/video) or SAM 3.1 (segmentation/vision); forcing a fit would mean bolting on a demo feature nobody at Scribase would ship.

Menivor (`/Users/arhansubasi/products/videogen`, live at menivor.com, repo `github.com/caelum0x/videogen`) is a production AI video-ad/UGC generation platform. It already runs a real provider-adapter registry with 11+ live cloud generation models (Kling, Luma, MiniMax/Hailuo, Runway Gen-4, Veo, Wan, Suno, HeyGen, SadTalker, ElevenLabs) plus a 4-provider image adapter (Stability, Black Forest Labs/Flux, Ideogram, Recraft), and two ad-creative product surfaces — Ad Studio and Ad Clone — that are the exact slot Muse Image/Spark/Wonder and SAM 3.1 drop into. This is the better pick. Draft below is for Menivor.

---

## Paste-ready application content

### Track

**Startup track.** Menivor is a shipped, live SaaS at menivor.com, not a weekend prototype: a generated OpenAPI contract with 247 paths / 281 operations, a 70-table Neon Postgres schema (SQLAlchemy 2 + Alembic), real billing (Stripe + iyzico), and four client surfaces (Next.js 15 web, Expo mobile, native Rust/GPUI desktop, FastAPI+Celery backend) on one versioned `/api/v1` contract. The hackathon's production-readiness judging criterion fits a real codebase with an existing adapter architecture better than a from-scratch build.

### Project idea (what we build in the 10 days)

Menivor turns a screen recording or a product photo into a finished ad/UGC video: script generation, TTS, an avatar presenter, karaoke captions, and compositing, already live end to end. Meta's Muse Image and SAM 3.1 are wired in as new routed providers today (built 2026-10-23, ahead of any hackathon acceptance, against Meta's already-public `dev.meta.ai` docs) — not a side demo, and not waiting on the build window to start.

Concretely: `app/domains/routing/providers/muse_image.py` and `sam_segment.py` follow the same adapter contract the codebase already uses for Kling (`kling_fal.py`: one real HTTP call, a 401/403/422/429 error taxonomy and backoff, shared via `KlingError`) and the shared `image.py` adapter that already serves Stability/Flux/Ideogram/Recraft — Muse Image is in fact OpenAI-Images-API compatible, so it speaks the identical `POST /v1/images/generations` / `/v1/images/edits` shape `openai_image.py` already uses. Both are registered in `registry.py`'s BYOK registry and in `media_catalog.py` (`meta/muse-image-1.0` + `-edit`, $0.01/image, license-gated paid-safe in `license_class.py`) behind the existing credential-gated pattern, activating only with a real `MODEL_API_KEY` — so Muse Image becomes selectable through the same OpenRouter-style `/images` gateway every other image provider (Stability/Flux/Ideogram/Recraft/OpenAI/Imagen) already routes through, the moment a key exists. (Muse Wonder/Spark turned out to be Meta's agentic *text/coding* models, not video generation — there is no Muse video model, so no `muse_video.py` was built; see the 2026-10-23 update above.)

On the vision side, Ad Studio's product-photo import (`adstudio/images.py`) normalized with plain Pillow (decode, decompression-bomb check, flatten to a white-canvas RGB JPEG) — no actual subject isolation. It now takes an optional, gated SAM 3.1 cutout step: when `MODEL_API_KEY` is set, SAM locates the product and the import crops to its bounding box (with a safe full-frame fallback) before the existing flatten runs; unconfigured, the output is byte-identical to before. The same primitive is now a helper in Ad Clone's keyframe vision pass (`adclone/vision.py`, `segment_subject` — same optional/lazy/"degrades to None" contract as the existing face-framing/OCR helpers), ready to thread into `ingest.py`'s per-shot observations once this runs against a live key. A real cutout mask is the difference between a generic background-swap and a usable ad variant; today it's a real bounding-box cutout, with Meta's officially-undocumented pixel-exact raster format tracked as the next step once a key is live (see `sam_segment.decode_boxes`'s docstring).

This is "Build for Your World": small businesses and creators have a specific, painful, already-searched-for problem — professional ad video without a production budget or editor — and Menivor already ships the full pipeline (script → TTS → avatar → captions → compose → publish) that Muse/SAM plug into as new generation backends on day one, not a greenfield toy.

### Technical skill (grounded in the current codebase)

Menivor (codename ReelForge internally) is a FastAPI + Celery + Redis + Neon Postgres backend with Next.js 15/React 19 web (deployed on Cloudflare Workers via OpenNext), Expo mobile, and a native Rust/GPUI desktop client, all consuming one versioned `/api/v1` contract exported to `packages/api-contract`. The routing domain (`app/domains/routing/`) implements a `ProviderRegistry` that only activates an adapter when its credential is present, plus BYOK adapter construction so a customer's own API key can be bound per request. The Kling adapter (`providers/kling_fal.py`) is a real integration against fal.ai's queue REST API — submit, poll with `queue_position`, fetch result, stream the MP4 to disk — with an explicit error taxonomy (401/403 fatal auth, 422 fatal content-policy, 429 honored via `Retry-After`) and a rule against blindly retrying ambiguous submission failures that may already be billable. The same pattern covers Luma, MiniMax/Hailuo, Runway Gen-4, Veo, Wan-Replicate, Suno, HeyGen, SadTalker, and ElevenLabs; a shared `ImageAdapter` serves four more providers (Stability, Black Forest Labs/Flux, Ideogram, Recraft).

Ad Studio (`app/domains/adstudio/`) imports a seller's product photos through an SSRF-guarded fetcher, decodes with Pillow (rejecting decompression bombs and non-images), normalizes to a size- and pixel-capped RGB JPEG, content-hashes for de-dup, and stores the result as an owned asset reusable by the rest of the platform's image-to-video generation. Ad Clone (`app/domains/adclone/`) resolves a competitor's ad link, downloads it, runs keyframe vision analysis (face-size framing, frame-to-frame camera-move via similarity transform, OCR, transcript), produces a heuristic-or-LLM-refined creative brief, and generates per-engine render plans under an explicit USD cost cap before any paid render runs. The test suite covering this (`tests/reelforge/`) is 463 files and roughly 5,882 test functions, run via `make -f Makefile.reelforge test`.

Links: live product — https://menivor.com. Repository — https://github.com/caelum0x/videogen (also published as https://github.com/caelum0x/menivor).

---

## Owner-only steps (not done here — needs real login/payment info)

1. Create/log into the Cerebral Valley account used to submit (https://cerebralvalley.ai/e/meta-ai-developer-hackathon) — login/2FA.
2. Paste the three sections above (track, project idea, technical skill) plus the two links into the actual application form fields.
3. Add your personal GitHub/LinkedIn profile links if the form asks for an individual profile rather than the repo URL — pick the identity you want judges to see.
4. Submit before 2026-10-25 11:59pm ET. Spots are first-come up to 20,000 — submit as soon as the pasted content is reviewed, do not wait for the deadline.
5. If accepted, any Meta Model API account/key setup for the 2026-10-26 to 2026-11-04 build window is an owner sign-up step (real credentials/payment).
