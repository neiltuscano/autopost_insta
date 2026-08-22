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

import os, sys, base64, json, argparse, time
from pathlib import Path
from datetime import datetime

import urllib.request, urllib.parse, urllib.error

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
CAPTIONS = {
    1: "🚀 Fresh H-1B & F-1 visa-sponsored jobs — Part 1/5!\nSwipe to explore today's top picks. All roles open to international candidates.\n\n#H1BJobs #F1Visa #VisaSponsorship #InternationalStudents #USJobs #TechJobs #f1jobs",
    2: "💼 More visa-friendly opportunities — Part 2/5!\nThese companies actively sponsor H-1B transfers & new petitions.\n\n#H1BSponsorship #F1OptJobs #InternationalTalent #USAJobs #SoftwareEngineer #f1jobs",
    3: "🌟 Top employers hiring right now — Part 3/5!\nAll roles include visa sponsorship. Drop a 🙋 if you're job hunting!\n\n#ImmigrationJobs #H1BTransfer #VisaFriendly #TechCareers #JobAlert #f1jobs",
    4: "⚡ Don't miss these — Part 4/5!\nRemote-friendly & hybrid roles that sponsor international workers.\n\n#RemoteWork #H1BVisa #F1Jobs #InternationalStudents #JobSearch #f1jobs",
    5: "🎯 Final batch of the day — Part 5/5!\nSave this post & share with someone who needs a visa-sponsored job!\n\n#JobOpportunity #H1B #F1Visa #VisaSponsored #USATech #f1jobs",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _api(method: str, path: str, params: dict | None = None) -> dict:
    """Call the Graph API; raises RuntimeError on any API or HTTP error."""
    if not IG_ACCESS_TOKEN:
        raise RuntimeError(
            "IG_ACCESS_TOKEN not set.\n"
            "  Run: python3 setup_ig_token.py --paste-token"
        )
    base_params = {"access_token": IG_ACCESS_TOKEN}
    if params:
        base_params.update(params)

    if method == "GET":
        url = f"{GRAPH_API_BASE}/{path}?{urllib.parse.urlencode(base_params)}"
        req = urllib.request.Request(url, method="GET")
    else:
        data = urllib.parse.urlencode(base_params).encode()
        req = urllib.request.Request(
            f"{GRAPH_API_BASE}/{path}", data=data, method=method
        )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body).get("error", {})
            raise RuntimeError(f"Graph API error {err.get('code')}: {err.get('message', body)}")
        except (json.JSONDecodeError, AttributeError):
            raise RuntimeError(f"HTTP {e.code}: {body[:300]}")

    if "error" in result:
        err = result["error"]
        raise RuntimeError(f"Graph API error {err.get('code')}: {err.get('message')}")
    return result


def upload_to_cloudinary(image_path: str) -> str:
    """Upload a local PNG to Cloudinary; returns the public HTTPS URL."""
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    data = urllib.parse.urlencode({
        "upload_preset": CLOUDINARY_UPLOAD_PRESET,
        "file":          f"data:image/png;base64,{image_b64}",
    }).encode()

    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Cloudinary upload failed ({e.code}): {e.read().decode()}") from e

    return result["secure_url"]


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
