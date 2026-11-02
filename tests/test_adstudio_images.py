"""Tests for the trimmed adstudio/images.py excerpt — the real SAM 3.1
integration call site (phrase_from_title + the cutout crop math), not the
bare adapter. Self-contained: no private storage/fetch types needed.
"""

from __future__ import annotations

import io

from PIL import Image

from app.domains.adstudio.images import (
    PRODUCT_PHRASE,
    _cropped_to_box,
    normalize_image,
    phrase_from_title,
)
from app.domains.routing.providers.sam_segment import SamBox


def test_phrase_from_title_cuts_at_middle_dot_variant_suffix():
    # Real case that broke the original regex (2026-11-02, Oxhan Atelier).
    assert phrase_from_title("Very Turkish Time Sweatshirt · Anka") == "the sweatshirt"


def test_phrase_from_title_handles_other_separators():
    assert phrase_from_title("Premium Leather Wallet - Brown") == "the wallet"
    assert phrase_from_title("Wireless Earbuds (White)") == "the earbuds"
    assert phrase_from_title("Running Shoes, Size 9") == "the shoes"


def test_phrase_from_title_falls_back_on_unusable_title():
    assert phrase_from_title("") == PRODUCT_PHRASE
    assert phrase_from_title("A") == PRODUCT_PHRASE


def test_cropped_to_box_rescales_and_pads():
    img = Image.new("RGB", (1000, 1000), (255, 255, 255))
    box = SamBox(x1=100, y1=100, x2=300, y2=300, frame_width=500, frame_height=500)
    cropped = _cropped_to_box(img, box)
    # SAM's box is in a 500x500 working frame; our image is 1000x1000 (2x), so
    # the crop should land around (200,200)-(600,600) plus 8% padding.
    assert 150 < cropped.size[0] < 500
    assert 150 < cropped.size[1] < 500


def test_normalize_image_with_cutout_disabled_matches_pre_sam_behavior():
    img = Image.new("RGB", (800, 600), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    out = normalize_image(buf.getvalue(), cutout=None)
    assert out is not None
    data, width, height = out
    assert (width, height) == (800, 600)


def test_normalize_image_crops_when_cutout_returns_a_box():
    img = Image.new("RGB", (800, 600), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    box = SamBox(x1=50, y1=50, x2=400, y2=300, frame_width=800, frame_height=600)
    out = normalize_image(buf.getvalue(), cutout=lambda _data: box)
    assert out is not None
    _data, width, height = out
    assert width < 800 and height < 600
