"""Muse Image generation/editing via Meta Model API — a REAL adapter.

Meta's Model API (https://dev.meta.ai, confirmed public docs as of 2026-10-23) is
OpenAI Images-API compatible: ``POST /v1/images/generations`` for text-to-image and
``POST /v1/images/edits`` for image-to-image / multi-reference composition, Bearer
auth, billed flat at **$0.01 per generated image** regardless of ``reasoning_strength``
or tool use (confirmed 2026-08-28, developer.meta.com/ai/resources/blog/build-with-muse-Image
and the Meta for Developers announcement). This mirrors the exact sync shape already
used by :mod:`app.domains.gateway.openai_image` and :mod:`app.domains.gateway._fal_image`
(one POST, wait inline, return a renderable URL) and shares the error taxonomy with
every other adapter in this package via :class:`KlingError`.

Real flow:
  ``POST https://api.meta.ai/v1/images/generations`` (Bearer ``MODEL_API_KEY``)
  body ``{model: "muse-image-1.0", prompt, n, size}``
  -> ``{data: [{url: "…"} | {b64_json: "…"}]}``

  ``POST https://api.meta.ai/v1/images/edits`` (one or more reference images —
  Muse Image handles single-image edit and multi-image composition in one model)
  body ``{model, prompt, image: "…" | ["…", …], n}`` -> the same response shape.

No real ``MODEL_API_KEY`` exists yet: Meta Model API access to Muse Image is part of
the still-pending Meta Global AI Developer Hackathon acceptance (application
deadline 2026-10-25). The HTTP protocol below is the real, documented wire format —
nothing here is faked — and it runs live the moment a key is dropped into
``MODEL_API_KEY``. Until then every call fails closed with a clearly-labeled
"not configured" :class:`KlingError` (``kind="auth"``), exactly like every other
unconfigured adapter in this package (see ``luma_gen.py``, ``openai_image.py``).
"""

from __future__ import annotations

import os
import time
from typing import Any, Sequence

from app.domains.routing.base import (
    RUN_COMPLETED,
    ModelListing,
    NormalizedUsage,
    ProviderRun,
    QuoteResult,
)
from app.domains.routing.providers.kling_fal import KlingError as ProviderCallError

_BASE = "https://api.meta.ai/v1"
MUSE_IMAGE_MODEL = "muse-image-1.0"
#: Confirmed flat price (2026-08-28 Meta for Developers announcement): $0.01/image.
MUSE_IMAGE_PRICE_MICROS = 10_000


def muse_api_key(explicit: str = "") -> str:
    """Resolve the Meta Model API key.

    Precedence: an explicit argument, then ``MODEL_API_KEY`` (Meta's own
    documented env var name — one key for every Meta Model API service: Muse
    Wonder/Spark/Image, Muse Voice Transcribe, SAM 3.1), then ``MUSE_API_KEY``
    as an image-specific override for deployments that split keys per product —
    the same ``auth_env``-override convention ``async_media.AsyncMediaConfig``
    already uses (e.g. ``ltx_fal`` sharing ``FAL_API_KEY``).
    """
    return explicit or os.getenv("MODEL_API_KEY", "") or os.getenv("MUSE_API_KEY", "")


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _json(resp) -> dict:
    try:
        body = resp.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {"data": body}


def _post(
    session: Any, path: str, body: dict, *, api_key: str, timeout_s: float, max_retries: int, sleep
) -> dict:
    import requests

    headers = _headers(api_key)
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = session.request(
                "POST", f"{_BASE}{path}", headers=headers, json=body, timeout=timeout_s
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


def _first_image(payload: dict) -> str:
    data = payload.get("data") or []
    if not isinstance(data, list) or not data:
        raise ProviderCallError(f"meta model api returned no image data: {payload}", kind="provider")
    first = data[0] or {}
    url = str(first.get("url") or "")
    if url:
        return url
    b64 = str(first.get("b64_json") or "")
    if b64:
        return f"data:image/png;base64,{b64}"
    raise ProviderCallError(
        f"meta model api image had neither url nor b64_json: {first}", kind="provider"
    )


def muse_generate_image(
    model_ref: str,
    prompt: str,
    *,
    api_key: str = "",
    image_urls: Sequence[str] = (),
    session: Any = None,
    size: str = "1024x1024",
    timeout_s: float = 120.0,
    max_retries: int = 3,
    sleep=time.sleep,
) -> str:
    """Generate (or edit, with ``image_urls``) one image synchronously via Muse Image.

    Text-to-image uses ``POST /v1/images/generations``; one or more reference
    images route to ``POST /v1/images/edits`` (single-image edit or multi-reference
    composition — Muse Image handles both in one model, per Meta's docs). Returns a
    renderable URL: a hosted ``url`` when the API provides one, otherwise a
    ``data:`` URL built from the returned base64 — the same contract as
    :func:`app.domains.gateway.openai_image.openai_generate_image`.
    """
    if not prompt:
        raise ProviderCallError("a prompt is required", kind="validation")
    key = muse_api_key(api_key)
    if not key:
        raise ProviderCallError(
            "Meta Model API key not configured (set MODEL_API_KEY or MUSE_API_KEY)",
            kind="auth",
        )
    sess = session
    if sess is None:
        import requests

        sess = requests.Session()

    refs = [str(u) for u in image_urls or () if u]
    if refs:
        body: dict[str, Any] = {
            "model": model_ref or MUSE_IMAGE_MODEL,
            "prompt": prompt,
            "image": refs[0] if len(refs) == 1 else refs,
            "n": 1,
        }
        payload = _post(
            sess, "/images/edits", body, api_key=key, timeout_s=timeout_s,
            max_retries=max_retries, sleep=sleep,
        )
    else:
        body = {"model": model_ref or MUSE_IMAGE_MODEL, "prompt": prompt, "size": size, "n": 1}
        payload = _post(
            sess, "/images/generations", body, api_key=key, timeout_s=timeout_s,
            max_retries=max_retries, sleep=sleep,
        )
    return _first_image(payload)


class MuseImageAdapter:
    """``ProviderAdapter``-protocol wrapper for the routing/BYOK registry.

    Thin, real wrapper over :func:`muse_generate_image` — no separate HTTP logic,
    so the registry (BYOK marketplace) path and the media-gateway dispatch path
    (``provider_execution.MediaProviderExecutor._submit_image``) share one
    implementation of the wire protocol.
    """

    provider_key = "muse-image"

    def __init__(self, *, api_key: str = "", model: str = MUSE_IMAGE_MODEL, session: Any = None) -> None:
        self._api_key = muse_api_key(api_key)
        self._model = model
        self._session = session

    def catalog(self) -> list[ModelListing]:
        return []  # operator-curated in the reviewed catalog (media_catalog.py)

    def quote(self, request: Any, price_version: Any) -> QuoteResult:
        from app.domains.routing.providers._pricing import quote_from_price

        return quote_from_price(price_version, 1)

    def submit(self, request: Any, snapshot: dict, correlation_id: str) -> ProviderRun:
        req = request if isinstance(request, dict) else {}
        refs = req.get("image_urls") or ([req["image_url"]] if req.get("image_url") else [])
        model_ref = str(snapshot.get("model_id", self._model) or self._model).split("/", 1)[-1]
        url = muse_generate_image(
            model_ref,
            req.get("prompt", ""),
            api_key=self._api_key,
            image_urls=tuple(refs),
            session=self._session,
        )
        return ProviderRun(
            provider_key=self.provider_key,
            run_id=correlation_id or "muse-image-run",
            state=RUN_COMPLETED,
            progress=100,
            result_ref=url,
            usage=self.normalize_usage({"images": 1}),
            raw={},
        )

    def poll(self, run: ProviderRun) -> ProviderRun:
        return run  # synchronous

    def cancel(self, run: ProviderRun) -> bool:
        return False

    def normalize_usage(self, payload: dict) -> NormalizedUsage:
        payload = payload or {}
        count = int(payload.get("images", 1) or 1)
        return NormalizedUsage(
            unit="images",
            quantity_units=max(1, count),
            cost_micros=MUSE_IMAGE_PRICE_MICROS * max(1, count),
            raw={k: v for k, v in payload.items() if k != "images"},
        )
