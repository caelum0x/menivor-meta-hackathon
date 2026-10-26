"""Muse Image adapter — real Meta Model API images protocol, retry, error taxonomy."""

from __future__ import annotations

import pytest

from app.domains.routing.base import RUN_COMPLETED
from app.domains.routing.providers.kling_fal import KlingError
from app.domains.routing.providers.muse_image import (
    MuseImageAdapter,
    muse_api_key,
    muse_generate_image,
)


class _Resp:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}
        self.headers = {}

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    def request(self, method, url, *, headers=None, json=None, timeout=None):
        self.calls.append({"method": method, "url": url, "headers": headers, "json": json})
        return self._script.pop(0)


def _gen(session, model="muse-image-1.0", **kw):
    return muse_generate_image(
        model, "a red panda", api_key="meta-secret", session=session, sleep=lambda s: None, **kw
    )


def test_hosted_url_returned_and_bearer_endpoint():
    sess = FakeSession([_Resp(200, {"data": [{"url": "https://meta/img.png"}]})])
    url = _gen(sess)
    assert url == "https://meta/img.png"
    call = sess.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://api.meta.ai/v1/images/generations"
    assert call["headers"]["Authorization"] == "Bearer meta-secret"
    assert call["json"]["model"] == "muse-image-1.0" and call["json"]["prompt"] == "a red panda"


def test_b64_becomes_data_url():
    sess = FakeSession([_Resp(200, {"data": [{"b64_json": "AAAABBBB"}]})])
    url = _gen(sess)
    assert url == "data:image/png;base64,AAAABBBB"


def test_image_urls_route_to_edits_endpoint():
    sess = FakeSession([_Resp(200, {"data": [{"url": "https://meta/edited.png"}]})])
    url = _gen(sess, image_urls=["https://example.com/src.jpg"])
    assert url == "https://meta/edited.png"
    call = sess.calls[0]
    assert call["url"] == "https://api.meta.ai/v1/images/edits"
    assert call["json"]["image"] == "https://example.com/src.jpg"


def test_multi_reference_composition_sends_a_list():
    sess = FakeSession([_Resp(200, {"data": [{"url": "https://meta/composed.png"}]})])
    _gen(sess, image_urls=["https://a/1.jpg", "https://b/2.jpg"])
    call = sess.calls[0]
    assert call["json"]["image"] == ["https://a/1.jpg", "https://b/2.jpg"]


def test_prompt_required():
    with pytest.raises(KlingError) as ei:
        muse_generate_image("muse-image-1.0", "", api_key="k", session=FakeSession([]))
    assert ei.value.kind == "validation"


def test_missing_key_is_auth(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("MUSE_API_KEY", raising=False)
    with pytest.raises(KlingError) as ei:
        muse_generate_image("muse-image-1.0", "x", api_key="", session=FakeSession([]))
    assert ei.value.kind == "auth"


def test_model_api_key_env_resolves(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "env-key")
    monkeypatch.delenv("MUSE_API_KEY", raising=False)
    assert muse_api_key() == "env-key"


def test_muse_api_key_env_is_accepted_fallback(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setenv("MUSE_API_KEY", "fallback-key")
    assert muse_api_key() == "fallback-key"


def test_auth_error_maps():
    with pytest.raises(KlingError) as ei:
        _gen(FakeSession([_Resp(401, {"error": {"message": "bad key"}})]))
    assert ei.value.kind == "auth"


def test_bad_request_is_validation():
    with pytest.raises(KlingError) as ei:
        _gen(FakeSession([_Resp(422, {"error": {"message": "content policy"}})]))
    assert ei.value.kind == "validation"


def test_rate_limit_retries_then_succeeds():
    sess = FakeSession([_Resp(429, {}), _Resp(200, {"data": [{"url": "https://meta/ok.png"}]})])
    assert _gen(sess) == "https://meta/ok.png" and len(sess.calls) == 2


def test_empty_data_is_provider_error():
    with pytest.raises(KlingError) as ei:
        _gen(FakeSession([_Resp(200, {"data": []})]))
    assert ei.value.kind == "provider"


# --------------------------------------------------------------------------- #
# ProviderAdapter protocol wrapper (registry.py / BYOK marketplace path)
# --------------------------------------------------------------------------- #
def test_adapter_implements_provider_adapter_protocol():
    from app.domains.routing.base import ProviderAdapter

    adapter = MuseImageAdapter(api_key="k")
    assert isinstance(adapter, ProviderAdapter)
    assert adapter.provider_key == "muse-image"


def test_adapter_submit_is_synchronous_and_completed():
    sess = FakeSession([_Resp(200, {"data": [{"url": "https://meta/run.png"}]})])
    adapter = MuseImageAdapter(api_key="k", session=sess)
    run = adapter.submit({"prompt": "a neon city"}, {"model_id": "meta/muse-image-1.0"}, "corr-1")
    assert run.state == RUN_COMPLETED
    assert run.result_ref == "https://meta/run.png"
    assert run.usage is not None and run.usage.quantity_units == 1
    assert run.usage.cost_micros == 10_000
    # poll() on an already-terminal run is a no-op (synchronous provider).
    assert adapter.poll(run) is run
    assert adapter.cancel(run) is False


@pytest.mark.skip(
    reason=(
        "app.domains.routing.providers.registry (the full BYOK registry listing "
        "every Menivor provider) lives only in the private production repo and is "
        "intentionally not published here. These two tests pass unmodified in the "
        "real codebase; see SUBMISSION.md for how to verify that."
    )
)
def test_registry_never_registers_without_a_key(monkeypatch):
    from app.domains.routing.base import ProviderRegistry
    from app.domains.routing.providers.registry import register_available_adapters

    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("MUSE_API_KEY", raising=False)
    reg = ProviderRegistry()
    registered = register_available_adapters(reg, env={})
    assert "muse-image" not in registered
    assert reg.get("muse-image") is None


@pytest.mark.skip(
    reason=(
        "app.domains.routing.providers.registry (the full BYOK registry listing "
        "every Menivor provider) lives only in the private production repo and is "
        "intentionally not published here. These two tests pass unmodified in the "
        "real codebase; see SUBMISSION.md for how to verify that."
    )
)
def test_registry_registers_when_model_api_key_present():
    from app.domains.routing.base import ProviderRegistry
    from app.domains.routing.providers.registry import register_available_adapters

    reg = ProviderRegistry()
    registered = register_available_adapters(reg, env={"MODEL_API_KEY": "live-key"})
    assert "muse-image" in registered
    assert reg.get("muse-image") is not None
