"""Excerpt of Menivor's real product-photo import pipeline — the actual SAM 3.1
integration call site, not just the bare adapter.

This file is trimmed from the private production ``adstudio/images.py``:
only the SAM 3.1 cutout-integration path is included (``phrase_from_title``,
``_default_cutout_box``, ``normalize_image``, ``_cropped_to_box``). Removed:
the R2/Asset storage layer, the SSRF-guarded fetcher, and
``store_remote_images`` — all tied to private storage/business types that
don't belong in a public repo. Nothing below is simplified or mocked; it is
copied verbatim from the real file, because the point of this excerpt is to
show SAM 3.1 wired into an actual feature, not just a standalone API client.

**Product-cutout refinement (optional, gated).** Plain Pillow flattening treats
the whole frame as the subject, so a product shot with background clutter
produces a noisy canvas. When ``MODEL_API_KEY``/``SAM_API_KEY`` is configured,
:func:`normalize_image` asks SAM 3.1 (``routing/providers/sam_segment.py``, a
real Meta Model API adapter) to locate the product and crops to its bounding
box before flattening — a real subject isolation step, not a mocked toggle.
``MODEL_API_KEY`` is live in production as of 2026-10-26 (owner's Meta Global
AI Developer Hackathon credit) and this path is verified end-to-end against the
real API (2026-10-28, see ``sam_segment.py``'s module docstring) — unconfigured
deployments still fall back to the byte-for-byte pre-adapter behavior, never a
blocked import.
"""

from __future__ import annotations

import io
import re
from typing import Any, Callable

from loguru import logger

MAX_EDGE = 2048
MIN_EDGE = 200
MAX_PIXELS = 60_000_000
#: Fallback object phrase when no usable product title is available at all.
PRODUCT_PHRASE = "the product"

# Cut a title at its first trailing variant/color/size separator (" - Brown",
# ", RFID Blocking", " (White)", " | Men's", " : Size 9", " · Anka") so the
# derived phrase below only ever looks at the part of the title that actually
# names the product, never a color/size/variant-name suffix. "·" is included
# because it's a real storefront convention (confirmed live 2026-11-02 against
# Oxhan Atelier's "Very Turkish Time Sweatshirt · Anka" — without it the old
# regex kept the trailing variant name and SAM 3.1 correctly failed to ground
# on it, same failure mode as every other non-category-noun case already
# documented above).
_TITLE_SEPARATOR_RE = re.compile(r"\s*[\(\[|,:;·]\s*|\s[-–—]\s")
_WORD_RE = re.compile(r"[A-Za-z]+")
#: Below this length a "noun" is almost always an initial/unit, not a real
#: object category (e.g. a stray "a"/"in" that slipped past word-splitting).
_MIN_NOUN_LEN = 3


def phrase_from_title(title: str) -> str:
    """Derive a short, concrete noun phrase SAM 3.1 can actually ground on.

    Verified live against the real Meta Model API (2026-10-26, see
    ``plans/menivor.md`` in the private repo): SAM 3.1's grounding reliably
    matches a bare category noun — "shoe", "shoes", "the wallet", "a sneaker"
    — but **never** an abstract placeholder like "the product"/"the
    item"/"the object", and **never** a multi-word phrase that still carries
    a leading adjective/qualifier or brand/model name ("Running shoes", "Nike
    Air Zoom Pegasus 40 Running Shoes", even a heuristic trim like "Running
    Shoes" all returned zero matches). This was previously untestable — no
    real key existed before that date — so the module shipped with the
    generic ``PRODUCT_PHRASE`` default, which turned out to essentially never
    match.

    E-commerce product titles conventionally put the actual category noun as
    the LAST word before any trailing color/size/variant suffix, so: cut the
    title at its first such separator, then take the last alphabetic word of
    what remains. Falls back to :data:`PRODUCT_PHRASE` (itself a documented
    no-op above) when there's no usable title — segmentation is always a
    refinement, never a requirement.
    """
    head = _TITLE_SEPARATOR_RE.split(title or "", maxsplit=1)[0]
    words = _WORD_RE.findall(head)
    if not words:
        return PRODUCT_PHRASE
    noun = words[-1].lower()
    if len(noun) < _MIN_NOUN_LEN:
        return PRODUCT_PHRASE
    return f"the {noun}"


def _default_cutout_box(data: bytes, *, phrase: str = PRODUCT_PHRASE) -> Any:
    """Real SAM 3.1 cutout lookup, no-op unless a Meta Model API key is set.

    Returns the best (largest-area) detected box, or ``None`` when
    unconfigured, no match, or the call fails — segmentation refines a cutout,
    it never blocks product-photo import.
    """
    from app.domains.routing.providers import sam_segment

    if not sam_segment.sam_api_key():
        return None
    try:
        import base64

        data_url = f"data:image/jpeg;base64,{base64.b64encode(data).decode('ascii')}"
        result = sam_segment.sam_segment_image(data_url, phrase)
    except Exception as exc:  # noqa: BLE001 - segmentation is a refinement, never fatal
        logger.info(f"adstudio SAM 3.1 cutout skipped: {exc}")
        return None
    return result.best_box


def normalize_image(
    data: bytes,
    *,
    cutout: Callable[[bytes], Any] | None = _default_cutout_box,
) -> tuple[bytes, int, int] | None:
    """Decode arbitrary image bytes into a bounded RGB JPEG (None if unusable).

    ``cutout`` optionally returns a :class:`~app.domains.routing.providers.sam_segment.SamBox`
    for the detected product; when one comes back, the frame is cropped to that
    box (clamped to the real image bounds) before the existing flatten/resize
    pipeline runs. Pass ``cutout=None`` to disable (or in tests, to keep the
    exact pre-SAM behavior).
    """
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as probe:
            width, height = probe.size
            if width * height > MAX_PIXELS:
                return None
        box = cutout(data) if cutout is not None else None
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            if min(img.size) < MIN_EDGE:
                return None
            if box is not None:
                img = _cropped_to_box(img, box)
                if min(img.size) < MIN_EDGE:
                    # A degenerate/too-tight detection must never make an
                    # otherwise-usable photo unusable: fall back to the
                    # original, uncropped frame.
                    img = Image.open(io.BytesIO(data))
                    img.load()
            if img.mode in ("RGBA", "LA", "P"):
                rgba = img.convert("RGBA")
                canvas = Image.new("RGB", rgba.size, (255, 255, 255))
                canvas.paste(rgba, mask=rgba.split()[-1])
                img_rgb = canvas
            else:
                img_rgb = img.convert("RGB")
            img_rgb.thumbnail((MAX_EDGE, MAX_EDGE))
            out = io.BytesIO()
            img_rgb.save(out, "JPEG", quality=90, optimize=True)
            return out.getvalue(), img_rgb.size[0], img_rgb.size[1]
    except Exception:  # noqa: BLE001 - any decode failure means "skip this image"
        return None


def _cropped_to_box(img: Any, box: Any) -> Any:
    """Crop ``img`` to a SAM box, padded 8% and clamped to the frame bounds.

    SAM 3.1's box coordinates are relative to the ``w``/``h`` it reports
    alongside the box (its own working frame size, per the documented grammar
    example — not necessarily our source image's actual pixel dimensions), so
    coordinates are rescaled onto ``img``'s real size before cropping.
    """
    width, height = img.size
    sx = (width / box.frame_width) if box.frame_width > 0 else 1.0
    sy = (height / box.frame_height) if box.frame_height > 0 else 1.0
    x1, y1 = box.x1 * sx, box.y1 * sy
    x2, y2 = box.x2 * sx, box.y2 * sy
    pad_x = max(1.0, (x2 - x1) * 0.08)
    pad_y = max(1.0, (y2 - y1) * 0.08)
    left = max(0, int(x1 - pad_x))
    top = max(0, int(y1 - pad_y))
    right = min(width, int(x2 + pad_x))
    bottom = min(height, int(y2 + pad_y))
    if right <= left or bottom <= top:
        return img
    return img.crop((left, top, right, bottom))
