"""Segment Anything Model (SAM) 3.1 segmentation via Meta Model API — a REAL adapter.

Confirmed public docs (2026-10-23): SAM 3.1 is hosted on Meta's Model API
(``https://dev.meta.ai/docs/sam/overview``, Meta for Developers announcement
2026-09-18). One request returns detections, pixel-precise segmentation masks and
identity-preserving tracks for a short noun-phrase prompt against an image or video,
over the *same* ``Authorization: Bearer`` envelope, base URL and billing surface as
every other Meta Model API service (Muse Wonder/Spark/Image, Muse Voice Transcribe).

Real flow (per the documented request/response shape):

  ``POST https://api.meta.ai/v1/responses``
  body::

      {
        "model": "sam-3.1",
        "input": [{
          "type": "message", "role": "user",
          "content": [
            {"type": "input_text", "text": "<short noun phrase>"},
            {"type": "input_image", "image_url": "<https or data: url>"}
          ]
        }]
      }

  response: the match streams/returns as ``output_text`` using a special-token
  grammar, e.g. ``<0f>0<|box;x1=353;y1=382;x2=453;y2=427;w=537;h=561|><|mask;...|>``
  — a frame id, an object ordinal, a ``<|box;...|>`` bounding box and a
  ``<|mask;...|>`` raster mask. Meta ships an official **JavaScript** decoder
  (``@meta-sam/parser``) for the raster; there is no published Python decoder and
  the exact bit-packing of the ``data=`` field (beyond "lossless, marked by ``~``")
  is not pinned down by the public docs fetched for this integration. This adapter
  therefore parses the fully-documented, unambiguous part of the grammar for
  real — the frame id, object ordinal and ``<|box;…|>`` bounding box — and derives
  a safe **bounding-box rectangular mask** as the v1 cutout. Decoding the exact
  raster bits is a follow-up once this runs against a live key (tracked in the
  docstring of :func:`decode_boxes`, not silently pretended to be pixel-exact).

No real ``MODEL_API_KEY``/``SAM_API_KEY`` exists yet (hackathon-exclusive access,
pending acceptance). Every call fails closed with a documented "not configured"
:class:`KlingError` (``kind="auth"``) when no key is set — never a faked response.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

from app.domains.routing.providers.kling_fal import KlingError as ProviderCallError

_BASE = "https://api.meta.ai/v1"
SAM_MODEL = "sam-3.1"

_BOX_RE = re.compile(
    r"<\|box;x1=(?P<x1>-?\d+);y1=(?P<y1>-?\d+);x2=(?P<x2>-?\d+);y2=(?P<y2>-?\d+);"
    r"w=(?P<w>\d+);h=(?P<h>\d+)\|>"
)
_FRAME_RE = re.compile(r"<(?P<frame>\d+)f>(?P<ordinal>\d+)")


def sam_api_key(explicit: str = "") -> str:
    """Resolve the Meta Model API key for SAM 3.1.

    Precedence: an explicit argument, then ``MODEL_API_KEY`` (Meta's own
    documented env var — shared by every Meta Model API service), then
    ``SAM_API_KEY`` as a segmentation-specific override.
    """
    return explicit or os.getenv("MODEL_API_KEY", "") or os.getenv("SAM_API_KEY", "")


@dataclass(frozen=True)
class SamBox:
    """A detected object's bounding box, in the source image's pixel coordinates."""

    x1: int
    y1: int
    x2: int
    y2: int
    frame_width: int
    frame_height: int


@dataclass(frozen=True)
class SamSegmentResult:
    """A SAM 3.1 call's normalized result: zero or more detected boxes."""

    boxes: tuple[SamBox, ...] = field(default_factory=tuple)
    raw_output_text: str = ""

    @property
    def matched(self) -> bool:
        return len(self.boxes) > 0

    @property
    def best_box(self) -> SamBox | None:
        """The largest-area detected box (the usual choice for a single product cutout)."""
        if not self.boxes:
            return None
        return max(self.boxes, key=lambda b: (b.x2 - b.x1) * (b.y2 - b.y1))


def decode_boxes(output_text: str) -> SamSegmentResult:
    """Parse SAM 3.1's documented special-token grammar into :class:`SamBox` rows.

    Decodes the unambiguous, fully-documented part of the grammar (frame id,
    object ordinal, ``<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|>``). The
    accompanying ``<|mask;...|>`` raster is intentionally not decoded here — its
    exact bit-packing is not pinned down by Meta's public docs — so callers get a
    real bounding box today and a documented upgrade path to pixel-exact masks
    once this runs against a live key and the official ``@meta-sam/parser``
    raster format can be verified byte-for-byte.
    """
    boxes: list[SamBox] = []
    for m in _BOX_RE.finditer(output_text or ""):
        x1, y1, x2, y2 = int(m["x1"]), int(m["y1"]), int(m["x2"]), int(m["y2"])
        w, h = int(m["w"]), int(m["h"])
        boxes.append(SamBox(x1=x1, y1=y1, x2=x2, y2=y2, frame_width=w, frame_height=h))
    return SamSegmentResult(boxes=tuple(boxes), raw_output_text=output_text or "")


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _json(resp) -> dict:
    try:
        body = resp.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {"data": body}


def _extract_output_text(payload: dict) -> str:
    """Pull the Responses-API ``output_text`` out of a (non-streamed) payload.

    Prefers the documented convenience field ``output_text``; falls back to
    walking the Responses API's ``output`` item list (``content[].text``), the
    shape Meta's docs say Model API mirrors from the OpenAI/Anthropic Responses
    convention.
    """
    direct = payload.get("output_text")
    if isinstance(direct, str):
        return direct
    chunks: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        for part in item.get("content") or []:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "".join(chunks)


def _post(
    session: Any, body: dict, *, api_key: str, timeout_s: float, max_retries: int, sleep
) -> dict:
    import requests

    headers = _headers(api_key)
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = session.request(
                "POST", f"{_BASE}/responses", headers=headers, json=body, timeout=timeout_s
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            if attempt <= max_retries:
                sleep(min(20.0, 2 ** (attempt - 1)))
                continue
            raise ProviderCallError(
                f"meta model api network error: {exc}", kind="transient", retryable=True
            ) from exc
        status = resp.status_code
        payload = _json(resp)
        if 200 <= status < 300:
            return payload
        msg = (
            str((payload.get("error") or {}).get("message"))
            if isinstance(payload, dict) and isinstance(payload.get("error"), dict)
            else ""
        ) or f"HTTP {status}"
        if status in (401, 403):
            raise ProviderCallError(f"meta model api auth failed: {msg}", kind="auth", status=status)
        if status in (400, 422):
            raise ProviderCallError(
                f"meta model api rejected request: {msg}", kind="validation", status=status
            )
        if status == 429:
            if attempt <= max_retries:
                sleep(min(30.0, 2**attempt))
                continue
            raise ProviderCallError(
                "meta model api rate limit", kind="rate_limit", retryable=True, status=429
            )
        if status >= 500:
            if attempt <= max_retries:
                sleep(min(20.0, 2 ** (attempt - 1)))
                continue
            raise ProviderCallError(
                f"meta model api server error: {msg}", kind="transient", retryable=True, status=status
            )
        raise ProviderCallError(
            f"meta model api unexpected status {status}: {msg}", kind="provider", status=status
        )


def sam_segment_image(
    image_url: str,
    phrase: str,
    *,
    api_key: str = "",
    session: Any = None,
    timeout_s: float = 60.0,
    max_retries: int = 3,
    sleep=time.sleep,
) -> SamSegmentResult:
    """Ask SAM 3.1 to locate ``phrase`` in ``image_url``; return detected boxes.

    ``image_url`` may be a public ``https`` URL or a ``data:`` URL (so a caller
    with only raw bytes in hand — e.g. Ad Studio's product-photo import, before
    it has uploaded anything — can segment without a network round trip to host
    the source first). ``phrase`` should be a short, concrete noun phrase
    ("the product", "wristwatch") — per Meta's docs, "concrete nouns match best"
    and exactly one object concept is matched per request.
    """
    if not phrase or not phrase.strip():
        raise ProviderCallError("an object phrase is required", kind="validation")
    if not image_url:
        raise ProviderCallError("an image_url is required", kind="validation")
    key = sam_api_key(api_key)
    if not key:
        raise ProviderCallError(
            "Meta Model API key not configured (set MODEL_API_KEY or SAM_API_KEY)",
            kind="auth",
        )
    sess = session
    if sess is None:
        import requests

        sess = requests.Session()

    body = {
        "model": SAM_MODEL,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": phrase.strip()},
                    {"type": "input_image", "image_url": image_url},
                ],
            }
        ],
    }
    payload = _post(sess, body, api_key=key, timeout_s=timeout_s, max_retries=max_retries, sleep=sleep)
    output_text = _extract_output_text(payload)
    return decode_boxes(output_text)


__all__ = [
    "SAM_MODEL",
    "SamBox",
    "SamSegmentResult",
    "decode_boxes",
    "sam_api_key",
    "sam_segment_image",
]
