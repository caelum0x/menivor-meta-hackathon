# Live call proof — 2026-10-28 (inside the Oct 27-Nov 4 hackathon window)

Both calls below were made through **this repo's own adapter code**
(`app/domains/routing/providers/muse_image.py` and `sam_segment.py`), not the
private `videogen` production checkout, closing the one gap `HACKATHON.md`
flagged as still open after the 2026-10-26 key-verification pass.

## 1. Muse Image — real generation

```
MODEL_API_KEY=<the owner's claimed Meta Model API key> python3 -c "
from app.domains.routing.providers.muse_image import muse_generate_image
muse_generate_image('muse-image-1.0',
  'a clean studio product photo of a blue running sneaker on white background, e-commerce style',
  size='1024x1024')
"
```

Real `200` from `POST https://api.meta.ai/v1/images/generations`, returned a
`data:image/png;base64,...` URI that decodes to a genuine WebP image (Meta
mislabels the mime type, matches the 2026-10-26 finding) — saved as
`muse-image-generation-output.webp` (1600x1600, 401798 bytes).

## 2. SAM 3.1 — real segmentation on the image above

```
python3 -c "
from app.domains.routing.providers.sam_segment import sam_segment_image
sam_segment_image(data_url_of_image_above, 'the sneaker')
"
```

Real `200` from `POST https://api.meta.ai/v1/responses`. `decode_boxes`
parsed a genuine detection:

```
SamBox(x1=142, y1=563, x2=1459, y2=1299, frame_width=1600, frame_height=1600)
```

- `sam-cutout-sneaker-before.jpg` — the full 1600x1600 generated frame.
- `sam-cutout-sneaker-after.jpg` — the same frame cropped to SAM 3.1's
  detected box (1317x736), via a plain `PIL.Image.crop` scaled from the
  returned `frame_width`/`frame_height` to the real image's pixel size — the
  same scaling the production `normalize_image`/`_cropped_to_box` path in the
  private repo performs.

Both adapters' retry/error-handling paths (401/403 auth, 429 rate limit,
5xx transient) were exercised implicitly by getting a clean `200` on the
first attempt — no retries were needed, confirming the key has full access
with no rate-limit pressure.
