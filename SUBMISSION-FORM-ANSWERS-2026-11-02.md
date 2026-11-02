# Cerebral Valley final submission form — paste-ready answers

Draft answers for the actual submission form (not the earlier application
form in `SUBMISSION.md`). Grounded in real code/real numbers already in this
repo and `DEMO-SCRIPT.md` — nothing invented. Submitting itself is owner-only
(needs your Cerebral Valley login).

**Team Name**: Menivor

**Team Members**: arhansuba (solo)

**Track**: Startup track

**Problem statement**: Build for Your World

**X post link**: leave blank (not competing for Most Viral Track)

**Project Description**:
> Menivor (menivor.com) turns a product photo or screen recording into a finished ad/UGC video — script, voice, captions, compositing — already live in production with real billing and 11+ cloud generation providers. For this hackathon we wired Meta's Muse Image and SAM 3.1 into Menivor's existing provider-routing registry: Muse Image slots into the same OpenAI-Images-API-compatible `/images` gateway every other image provider (Stability, Flux, Ideogram, Recraft) already uses, and SAM 3.1 gives Ad Studio's product-photo import a real subject cutout instead of a full-frame flatten. Both are live, tested, and verified against the real Meta Model API key — not a hackathon-only demo feature bolted onto a side project.

**Public GitHub Repository**: https://github.com/caelum0x/menivor-meta-hackathon

**3-Minute Demo Video**: *(owner step — upload the rendered MP4 to YouTube and paste the link here. Video is being produced now; see handoff note for the file path once it lands.)*

**Describe your use of Meta products to build the submitted project**:
> We integrated two Meta Model API services directly into Menivor's production provider-routing architecture (`app/domains/routing/providers/`): Muse Image (`muse-image-1.0`, `POST /v1/images/generations` + `/v1/images/edits`) for ad-creative image generation/editing, and SAM 3.1 (`POST /v1/responses`, noun-phrase-grounded segmentation) for real product-photo subject cutout in Ad Studio. Both follow the exact same adapter contract (error taxonomy, retry/backoff, BYOK registry) as our 11 existing cloud providers, so they became selectable the moment a real `MODEL_API_KEY` existed — zero new UI, zero new customer-facing code path.

**Why are Meta's models important to your solution?**:
> Our whole platform bet is that new models should drop into one abstraction, not require a bespoke integration each time. Muse Image's OpenAI-Images-API compatibility proved that bet works for a real third-party model with zero adapter rewrites. SAM 3.1 gave our sellers a real capability (actual subject detection) we had never had before — Ad Studio could only flatten onto a white canvas; it's never been able to find the product in the frame until this.

**Partner feedback (Fireworks, Modal, Baseten)**:
> Not used — we called Meta's Model API directly with our own `MODEL_API_KEY` and didn't need partner inference credits for either Muse Image or SAM 3.1's hosted endpoints.

---

## Subjective/rating questions — owner's honest call, not mine to fabricate

These are opinion questions about *your* experience. I'm not going to invent
a persona's feelings — pick what you actually think. Real, true context to
inform each:

- **How likely to build with Meta Model API again / recommend it**: real experience was positive — real docs, real working endpoints, clean OpenAI-shape compatibility for Muse Image. Worth reflecting that honestly.
- **Recommend Muse Code**: we never touched it (it's an unrelated CLI coding agent, not part of this integration) — honest answer is "N/A / no opinion," not a rating.
- **Biggest obstacle hit**: real, specific, true — SAM 3.1's grounding only matches a *bare* concrete noun ("shoe", "the shoes") and fails the instant the phrase carries an adjective or brand name ("Running shoes" failed; "shoes" on the identical photo matched). Our shipped default phrase (`"the product"`) was silently a no-op until we fixed it with a real title-derived noun extractor.
- **Compared with other models for the same work**: Muse Image is the first provider in our registry that's natively OpenAI-Images-API-compatible, so integration cost was near zero compared to Stability/Flux/Ideogram/Recraft, which each needed their own request/response mapping. SAM 3.1 is genuinely new capability for us — we had zero segmentation before it.
- **What matters most choosing a model/tool**: documented, stable request/response shape (so it drops into an existing abstraction) and a real, predictable error taxonomy — not raw benchmark numbers.
- **Hardest to switch away from**: the adapter investment itself (tests, error handling, registry wiring) — not model lock-in; swapping the underlying model is cheap once the adapter contract is right.
- **What would stop you using Meta's models in production**: two real, honest gaps found building this — SAM 3.1 has no published per-call price anywhere we could find, and its pixel-exact raster mask format has no public Python decoder (only an official JS one), so today we only get a bounding-box cutout, not a pixel-exact mask.
