"""Seed floc-morphology micrographs for the TEST_ Sludge Microscopy campaign.

sql/seed_demo.sql creates the campaign, the single-series LabPanel and the BR-400
sludge grab samples, but not the images: files, metadata and thumbnails are all
produced by the API's own ingest path. Run this against a live stack:

    docker compose up -d
    uv run scripts/seed_sludge_images.py            # default http://localhost:8000
    uv run scripts/seed_sludge_images.py http://api:8000

Idempotency: re-running adds another replicate per sample. Re-seed the DB instead.
"""

import io
import os
import random
import sys

import httpx
from PIL import Image, ImageDraw, ImageFilter

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
TOKEN = os.getenv("API_SERVICE_TOKEN", "dev-service-token")
SAMPLE_PREFIX = "TEST_ Sludge grab BR-400"
CAMPAIGN_NAME = "TEST_ Sludge Microscopy 2026"
SAMPLING_POINT = "TEST_ Bioreactor 4"
SERIES_NAME = "TEST_ Sludge floc morphology at Bioreactor 4"
PARAMETER_ID = 16  # floc_morphology
UNIT_ID = 11  # dimensionless


def micrograph(seed: int, filaments: int) -> bytes:
    """A plausible phase-contrast floc image: dark irregular flocs + filaments."""
    rng = random.Random(seed)
    img = Image.new("RGB", (640, 480), (222, 222, 216))
    draw = ImageDraw.Draw(img)
    for _ in range(rng.randint(12, 20)):  # flocs
        cx, cy = rng.randint(40, 600), rng.randint(40, 440)
        for _ in range(rng.randint(6, 14)):  # lobes make the outline irregular
            r = rng.randint(8, 30)
            x, y = cx + rng.randint(-25, 25), cy + rng.randint(-25, 25)
            grey = rng.randint(90, 150)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(grey, grey, grey - 5))
    for _ in range(filaments):  # filamentous bacteria extending from the flocs
        x, y = rng.randint(0, 640), rng.randint(0, 480)
        pts = [(x, y)]
        for _ in range(rng.randint(6, 14)):
            x += rng.randint(-30, 30)
            y += rng.randint(-30, 30)
            pts.append((x, y))
        draw.line(pts, fill=(70, 70, 70), width=2)
    return _png(img.filter(ImageFilter.GaussianBlur(0.8)))


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def main() -> None:
    client = httpx.Client(
        base_url=API,
        timeout=30.0,
        headers={"Authorization": f"Bearer {TOKEN}"},  # dev service token
    )

    campaigns = client.get("/api/v1/campaigns").raise_for_status().json()
    campaign_id = next(c["campaign_id"] for c in campaigns if c["name"] == CAMPAIGN_NAME)

    points = client.get("/api/v1/ingest/lookup/sampling-points").raise_for_status().json()
    sampling_point_id = next(
        p["sampling_point_id"] for p in points if p["label"] == SAMPLING_POINT
    )

    samples = client.get("/api/v1/ingest/lookup/samples").raise_for_status().json()
    sludge = sorted(
        (s for s in samples if s["label"].startswith(SAMPLE_PREFIX)),
        key=lambda s: s["sample_date"],
    )
    if not sludge:
        raise SystemExit(f"No samples labelled '{SAMPLE_PREFIX}*' — is seed_demo.sql loaded?")

    # More filaments each week: a bulking episode the Explore image viewer can show.
    for i, sample in enumerate(sludge):
        image = micrograph(seed=i, filaments=4 + 8 * i)
        resp = client.post(
            "/api/v1/ingest/lab-image",
            data={
                "name": f"TEST_ Floc microscopy {sample['sample_date'][:10]}",
                "experiment_datetime": sample["sample_date"].replace(" ", "T"),
                "sample_id": sample["sample_id"],
                "parameter_id": PARAMETER_ID,
                "sampling_point_id": sampling_point_id,
                "unit_id": UNIT_ID,
                "series_name": SERIES_NAME,
                "campaign_id": campaign_id,
                "description": "Phase-contrast micrograph of BR-400 mixed-liquor grab",
                "quality_code": 1,
            },
            files=[("images", (f"floc_{i}.png", image, "image/png"))],
        )
        resp.raise_for_status()
        print(f"{sample['label']}: {resp.json()['storage_paths']}")


if __name__ == "__main__":
    main()
