"""SAM 3.1 adapter — real Meta Model API Responses protocol, box-grammar decode, error taxonomy."""

from __future__ import annotations

import pytest

from app.domains.routing.providers.kling_fal import KlingError
from app.domains.routing.providers.sam_segment import (
    decode_boxes,
    sam_api_key,
    sam_segment_image,
)

_EXAMPLE_OUTPUT = (
    "<0f>0<|box;x1=353;y1=382;x2=453;y2=427;w=537;h=561|>"
    "<|mask;x=0;y=0;data=46,101,~...|>"
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


def _call(session, **kw):
    return sam_segment_image(
        "https://example.com/street.png", "yellow school bus",
        api_key="meta-secret", session=session, sleep=lambda s: None, **kw
    )


# --------------------------------------------------------------------------- #
# Grammar decode — the fully-documented, unambiguous part
# --------------------------------------------------------------------------- #
def test_decode_boxes_parses_the_documented_example():
    result = decode_boxes(_EXAMPLE_OUTPUT)
    assert result.matched is True
    box = result.best_box
    assert (box.x1, box.y1, box.x2, box.y2) == (353, 382, 453, 427)
    assert (box.frame_width, box.frame_height) == (537, 561)


def test_decode_boxes_empty_text_means_no_match():
    assert decode_boxes("").matched is False
    assert decode_boxes("").best_box is None


def test_decode_boxes_picks_largest_area_box():
    text = (
        "<0f>0<|box;x1=0;y1=0;x2=10;y2=10;w=100;h=100|>"
        "<1f>1<|box;x1=0;y1=0;x2=50;y2=50;w=100;h=100|>"
    )
    box = decode_boxes(text).best_box
    assert (box.x2 - box.x1) * (box.y2 - box.y1) == 2500


# --------------------------------------------------------------------------- #
# Real HTTP protocol (Responses API envelope, Bearer auth, Meta error taxonomy)
# --------------------------------------------------------------------------- #
def test_real_request_shape_and_output_text_field():
    sess = FakeSession([_Resp(200, {"output_text": _EXAMPLE_OUTPUT})])
    result = _call(sess)
    assert result.matched is True
    call = sess.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://api.meta.ai/v1/responses"
    assert call["headers"]["Authorization"] == "Bearer meta-secret"
    assert call["json"]["model"] == "sam-3.1"
    content = call["json"]["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "yellow school bus"}
    assert content[1] == {"type": "input_image", "image_url": "https://example.com/street.png"}


def test_responses_api_output_items_fallback():
    # When the convenience ``output_text`` field is absent, fall back to the
    # Responses API's ``output[].content[].text`` item shape.
    payload = {
        "output": [
            {"content": [{"type": "output_text", "text": _EXAMPLE_OUTPUT}]},
        ]
    }
    sess = FakeSession([_Resp(200, payload)])
    result = _call(sess)
    assert result.matched is True


def test_no_match_is_empty_not_an_error():
    sess = FakeSession([_Resp(200, {"output_text": ""})])
    result = _call(sess)
    assert result.matched is False


def test_phrase_required():
    with pytest.raises(KlingError) as ei:
        sam_segment_image("https://x/img.png", "", api_key="k", session=FakeSession([]))
    assert ei.value.kind == "validation"


def test_image_url_required():
    with pytest.raises(KlingError) as ei:
        sam_segment_image("", "a bus", api_key="k", session=FakeSession([]))
    assert ei.value.kind == "validation"


def test_missing_key_is_auth(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("SAM_API_KEY", raising=False)
    with pytest.raises(KlingError) as ei:
        sam_segment_image("https://x/img.png", "a bus", api_key="", session=FakeSession([]))
    assert ei.value.kind == "auth"


def test_model_api_key_env_resolves(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "env-key")
    monkeypatch.delenv("SAM_API_KEY", raising=False)
    assert sam_api_key() == "env-key"


def test_sam_api_key_env_is_accepted_fallback(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setenv("SAM_API_KEY", "fallback-key")
    assert sam_api_key() == "fallback-key"


def test_auth_error_maps():
    with pytest.raises(KlingError) as ei:
        _call(FakeSession([_Resp(401, {"error": {"message": "bad key"}})]))
    assert ei.value.kind == "auth"


def test_rate_limit_retries_then_succeeds():
    sess = FakeSession([_Resp(429, {}), _Resp(200, {"output_text": _EXAMPLE_OUTPUT})])
    result = _call(sess)
    assert result.matched is True and len(sess.calls) == 2
