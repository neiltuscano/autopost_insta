"""
f1jobs — Instagram Auto-Poster (direct Graph API)
Uploads carousel images to Cloudinary (public CDN), then posts
them to Instagram via the Graph API.

Setup (one-time):
  1. Run setup_ig_token.py to write IG_ACCESS_TOKEN & IG_ACCOUNT_ID to .env
  2. In config.py (or .env), confirm CLOUDINARY_CLOUD_NAME and
     CLOUDINARY_UPLOAD_PRESET match your Cloudinary account settings.

Usage:
  python poster.py --carousel 1            # post carousel 1 (5 images)
  python poster.py --carousel 1 --dry-run  # preview without posting
"""
from __future__ import annotations

import os, sys, base64, json, argparse, time, socket
from pathlib import Path
from datetime import datetime

import urllib.request, urllib.parse, urllib.error

# Hard timeout for ALL socket operations including DNS resolution.
# Without this, a DNS failure on macOS hangs for ~25 min per attempt.
socket.setdefaulttimeout(30)

# ── Config ────────────────────────────────────────────────────────────────────

def _load_env():
    """Load key=value pairs from .env in the project root."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

IG_ACCESS_TOKEN          = os.getenv("IG_ACCESS_TOKEN",          "")
IG_ACCOUNT_ID            = os.getenv("IG_ACCOUNT_ID",            "")
CLOUDINARY_CLOUD_NAME    = os.getenv("CLOUDINARY_CLOUD_NAME",    "qvinwyy0")
CLOUDINARY_UPLOAD_PRESET = os.getenv("CLOUDINARY_UPLOAD_PRESET", "f1jobs")
GRAPH_API_BASE           = "https://graph.facebook.com/v26.0"

# Captions per carousel slot
# Carousels 1-3 → entry-level / new grad focus
# Carousels 4-5 → senior / experienced roles
CAPTIONS = {
    1: "🎓 New Grad Alert! Entry-level roles with H-1B sponsorship — Part 1/5!\nAll roles welcome F-1 OPT & H-1B applicants. 0–2 years experience needed.\n\n#NewGrad #H1BJobs #F1Visa #OPT #EntryLevel #USJobs #NewGradJobs #f1jobs",
    2: "🎓 More entry-level opportunities for international grads — Part 2/5!\nThese top companies sponsor H-1B & OPT. Get your foot in the door! 🚪\n\n#NewGradJobs #H1BSponsorship #F1OptJobs #EntryLevelTech #InternationalStudents #f1jobs",
    3: "🎓 Hot entry-level picks of the day — Part 3/5!\nSwipe to find your next role. All positions sponsor H-1B & F-1 OPT. Drop a 🙋 if you're job hunting!\n\n#H1BNewGrad #OPTJobs #VisaFriendly #EntryLevelSWE #TechJobs #f1jobs",
    4: "⚡ Senior & experienced roles with visa sponsorship — Part 4/5!\n3+ years exp · Remote-friendly · H-1B transfer welcome.\n\n#SeniorEngineer #H1BVisa #F1Jobs #InternationalTalent #RemoteWork #f1jobs",
    5: "🎯 Top senior picks of the day — Part 5/5!\nSave this post & share with someone who needs a visa-sponsored role!\n\n#JobOpportunity #H1B #F1Visa #VisaSponsored #SeniorDev #USATech #f1jobs",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _api(method: str, path: str, params: dict | None = None, retries: int = 3) -> dict:
    """Call the Graph API; raises RuntimeError on any API or HTTP error.
    Retries up to `retries` times with exponential backoff on network timeouts.
    """
    if not IG_ACCESS_TOKEN:
        raise RuntimeError(
            "IG_ACCESS_TOKEN not set.\n"
            "  Run: python3 setup_ig_token.py --paste-token"
        )
    base_params = {"access_token": IG_ACCESS_TOKEN}
    if params:
        base_params.update(params)

    for attempt in range(1, retries + 1):
        if method == "GET":
            url = f"{GRAPH_API_BASE}/{path}?{urllib.parse.urlencode(base_params)}"
            req = urllib.request.Request(url, method="GET")
        else:
            data = urllib.parse.urlencode(base_params).encode()
            req = urllib.request.Request(
                f"{GRAPH_API_BASE}/{path}", data=data, method=method
            )

        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                result = json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                err = json.loads(body).get("error", {})
                raise RuntimeError(f"Graph API error {err.get('code')}: {err.get('message', body)}")
            except (json.JSONDecodeError, AttributeError):
                raise RuntimeError(f"HTTP {e.code}: {body[:300]}")
        except OSError as e:
            if attempt == retries:
                raise RuntimeError(f"Graph API call failed after {retries} attempts: {e}") from e
            wait = 2 ** attempt  # 2s, 4s, 8s
            print(f"\n  ⚠  Network error (attempt {attempt}/{retries}), retrying in {wait}s… ({e})")
            time.sleep(wait)
            continue

        if "error" in result:
            err = result["error"]
            raise RuntimeError(f"Graph API error {err.get('code')}: {err.get('message')}")
        return result


def upload_to_cloudinary(image_path: str, retries: int = 3) -> str:
    """Upload a local PNG to Cloudinary; returns the public HTTPS URL.
    Retries up to `retries` times with exponential backoff on network errors.
    """
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    data = urllib.parse.urlencode({
        "upload_preset": CLOUDINARY_UPLOAD_PRESET,
        "file":          f"data:image/png;base64,{image_b64}",
    }).encode()

    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"

    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                result = json.loads(r.read())
            return result["secure_url"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Cloudinary upload failed ({e.code}): {e.read().decode()}") from e
        except OSError as e:
            if attempt == retries:
                raise RuntimeError(f"Cloudinary upload failed after {retries} attempts: {e}") from e
            wait = 2 ** attempt  # 2s, 4s, 8s
            print(f"  ⚠  Upload error (attempt {attempt}/{retries}), retrying in {wait}s… ({e})")
            time.sleep(wait)


# ── Instagram Graph API posting ───────────────────────────────────────────────

def _wait_for_container(container_id: str, timeout: int = 60) -> None:
    """Poll until the media container status is FINISHED (or error out)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = _api("GET", container_id, {"fields": "status_code"})
        status = result.get("status_code", "")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} entered ERROR state")
        time.sleep(3)
    raise RuntimeError(f"Container {container_id} did not reach FINISHED within {timeout}s")


def post_carousel_to_instagram(image_urls: list, caption: str) -> str:
    """
    Full Instagram Graph API carousel post flow:
      1. Create individual media containers (one per image)
      2. Create carousel container referencing all items
      3. Wait for carousel container to be FINISHED
      4. Publish
    Returns the published media ID.
    """
    if not IG_ACCOUNT_ID:
        raise RuntimeError(
            "IG_ACCOUNT_ID not set.\n"
            "  Run: python3 setup_ig_token.py --paste-token"
        )

    # Step 1: create individual item containers
    item_ids = []
    for i, url in enumerate(image_urls, 1):
        print(f"    Creating container {i}/{len(image_urls)}…", end=" ", flush=True)
        result = _api("POST", f"{IG_ACCOUNT_ID}/media", {
            "image_url":        url,
            "is_carousel_item": "true",
            "media_type":       "IMAGE",
        })
        item_ids.append(result["id"])
        print(f"✓ ({result['id']})")
        time.sleep(1)

    # Step 2: create carousel container
    print(f"\n    Building carousel container…", end=" ", flush=True)
    carousel = _api("POST", f"{IG_ACCOUNT_ID}/media", {
        "media_type": "CAROUSEL",
        "children":   ",".join(item_ids),
        "caption":    caption,
    })
    carousel_id = carousel["id"]
    print(f"✓ ({carousel_id})")

    # Step 3: wait for FINISHED status
    print(f"    Waiting for container to be ready…", end=" ", flush=True)
    _wait_for_container(carousel_id)
    print("✓")

    # Step 4: publish
    print(f"    Publishing…", end=" ", flush=True)
    pub = _api("POST", f"{IG_ACCOUNT_ID}/media_publish", {"creation_id": carousel_id})
    media_id = pub["id"]
    print(f"✓  (media_id={media_id})")
    return media_id


# ── Main poster ───────────────────────────────────────────────────────────────

def post_carousel(carousel_num: int, dry_run: bool = False) -> None:
    """Upload images from output/ to Cloudinary and post carousel to Instagram."""
    from config import OUTPUT_DIR

    out = Path(str(OUTPUT_DIR))
    prefix = f"carousel_{carousel_num:02d}_"
    images = sorted(out.glob(f"{prefix}*.png"))

    if not images:
        print(f"  ✗  No images found for carousel {carousel_num} in {out}/")
        print(f"      Run: python daily_run.py --carousel {carousel_num}")
        sys.exit(1)

    EXPECTED = 6  # 1 cover + 5 job cards
    if len(images) > EXPECTED:
        print(f"  ⚠  Found {len(images)} images for carousel {carousel_num} (expected {EXPECTED}).")
        print(f"      Picking the {EXPECTED} most recently modified. Clean output/ to avoid this.")
        images = sorted(images, key=lambda p: p.stat().st_mtime, reverse=True)[:EXPECTED]
        images = sorted(images)  # restore filename order (cover first)

    caption = CAPTIONS.get(carousel_num, CAPTIONS[1])

    print(f"\n{'='*60}")
    print(f"  f1jobs Poster — Carousel {carousel_num}/5")
    print(f"  Images : {len(images)}")
    print(f"  Posted : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    if dry_run:
        print("\n  [DRY RUN] Would post these images:")
        for img in images:
            print(f"    • {img.name}")
        print(f"\n  [DRY RUN] Caption:\n{caption}")
        print("\n  [DRY RUN] No uploads or API calls made.")
        return

    # 1. Upload images to Cloudinary for public URLs
    print("\n  [1/2]  Uploading images to Cloudinary…")
    image_urls = []
    for img in images:
        print(f"    Uploading {img.name}…", end=" ", flush=True)
        url = upload_to_cloudinary(str(img))
        image_urls.append(url)
        print(f"✓")
        time.sleep(0.5)

    # 2. Post directly via Instagram Graph API
    print("\n  [2/2]  Posting to Instagram via Graph API…")
    media_id = post_carousel_to_instagram(image_urls, caption)

    print(f"\n  ✓  Carousel {carousel_num}/5 posted! (media_id={media_id})")
    print(f"  Posted to IG account {IG_ACCOUNT_ID}")

    # Clean up — delete images now that they're live on Instagram
    print(f"  Cleaning up {len(images)} image(s)…", end=" ", flush=True)
    for img in images:
        try:
            img.unlink()
        except OSError as e:
            print(f"\n  ⚠  Could not delete {img.name}: {e}")
    print("✓")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="f1jobs Instagram poster")
    parser.add_argument("--carousel", type=int, required=True, choices=range(1, 6),
                        help="Which carousel to post (1-5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be posted without making any API calls")
    args = parser.parse_args()
    post_carousel(args.carousel, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
