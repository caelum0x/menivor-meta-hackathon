# Demo video script — 3 minutes, for Meta Global AI Developer Hackathon submission

Requirement (per the hackathon rules): public repo + a 3-minute demo video +
a live product. This is the shot list the owner (or whoever records it) should
follow once a real `MODEL_API_KEY` is set on the Menivor production API.
Everything below is a real, already-built screen to record — no placeholder
screens, no staged data.

**Framing for this cut: pitch it like Meta could genuinely invest in or acquire
this, not just judge a submission.** Every claim below is grounded in what's
actually true today (real live product, real billing, real infra) — the
ambition is in the vision and the architecture story, not in invented traction
numbers. Honest numbers as of 2026-10-26: live at menivor.com, real Dodo
billing wired and tested end-to-end, 11 cloud video/image providers already
integrated behind one routing registry, ~10 real outside signups so far, 0
paying customers yet (a real, recently-fixed bug — a paid-access gate was
silently blocking the entire free-tier share/referral loop — was the reason
nobody could convert; that's fixed and live now). Don't inflate past this. The
pitch is "real product, real infra, real fixed-as-we-go engineering, early
traction" — not "already big."

Recording notes: screen-record at 1080p+, 16:9 (Cerebral Valley submission
page), narrate live or dub afterward with Menivor's own TTS (Kokoro/edge-tts,
same engine the product uses for its own reels — fitting, since Menivor's
whole pitch is "turn a screen recording into a narrated video").

## 0:00–0:20 — Hook + the real size of the problem

Shot: menivor.com homepage, hero "Paste a link. Get a TikTok-ready video."
Narration: "Every seller, creator, and small business needs video ads, and
almost none of them can afford a production budget. Menivor turns a product
photo or a screen recording into a finished ad — script, voice, captions,
all automatic. This isn't a concept: it's live today at menivor.com, with
real Dodo billing, real cloud rendering across 11 providers, and real mobile
and desktop apps already shipped."

## 0:20–0:50 — The problem Muse Image + SAM 3.1 solve

Shot: Ad Studio's product-photo import screen, upload a real product photo
with a busy/non-white background.
Narration: "Sellers upload product photos straight from their phone — messy
backgrounds, bad crops. Before this hackathon, Menivor could only flatten the
image onto a white canvas. It couldn't actually find the product in the
frame. That's a real quality ceiling on a real product people already use."

## 0:50–1:40 — SAM 3.1 in action (the real, new thing)

Shot: trigger the Ad Studio import with `MODEL_API_KEY` set; show (via logs
or an inspector overlay, or the before/after crop) that SAM 3.1 located the
product and the import now crops to the detected bounding box instead of the
full frame.
Narration: "We wired Meta's SAM 3.1 into Menivor's existing provider-routing
registry — the same architecture that already routes 11 other cloud models
in production. That's the real point: this isn't a one-off integration bolted
on for a hackathon, it's one more model dropped into an abstraction built to
scale to dozens. One call to Meta's Model API, and the product import now
gets a real subject cutout before the ad render starts. [point at the
before/after] Left: the old white-canvas flatten. Right: SAM found the
actual product."

## 1:40–2:20 — Muse Image in action

Shot: trigger an Ad Studio/Ad Clone generation that calls Muse Image through
the media gateway (`meta/muse-image-1.0`), show the generated/edited image
land in the project the same way a Flux/Ideogram/Stability result would.
Narration: "Muse Image is OpenAI-Images-API compatible, so it slotted into
the exact same `/images` gateway every other image provider already uses —
Stability, Flux, Ideogram, Recraft. Zero new UI, zero new code path for the
customer. That's the architectural bet this whole product is built on: new
Meta models become instantly available to every existing Menivor user the
moment a key exists, with no re-engineering. That's what makes this a
platform, not a wrapper around one model."

## 2:20–2:50 — Why this matters beyond the demo

Shot: Megaphone's live manifest (media.menivor.com) or the pricing page, plus
(if it still shows cleanly) the funnel/growth dashboard.
Narration: "Menivor already has real sellers signing up for professional ad
video without a production budget — and real, fast engineering behind it: we
found and shipped a fix just this week for a paid-access bug that was
silently blocking every free user from ever sharing a reel, the core of our
own referral loop. That's the kind of velocity a growing platform needs.
SAM-based product cutout and Muse Image give those same users a cleaner
result using Meta's own models, on infrastructure we already ship and bill
against today — not a weekend toy bolted onto a side project. We think this
is exactly the kind of real, extensible surface Meta's models should be
distributed through at scale."

## 2:50–3:00 — Close

Shot: menivor.com + GitHub repo QR/URL on screen.
Narration: "Live at menivor.com. Code at github.com/caelum0x/menivor-meta-hackathon.
Built on Meta's Model API — and built to grow with it."

## Still blocked on (owner-only, not something an agent can do)

A real recording of 0:50–2:20 needs a live `MODEL_API_KEY` set in Menivor's
production environment — i.e., the owner must first claim the Meta API
credits (card-on-file). Until then, this script can be rehearsed against the
adapters' own fail-closed error message ("Meta Model API key not configured")
to time the cuts, but the actual before/after crop and generated image shots
cannot be captured for real.
