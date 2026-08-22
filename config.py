"""
f1jobs — Central Config
All paths, credentials, and settings live here.
Edit this file or set values in .env to configure the project.
"""

import os
import urllib.request
from pathlib import Path

# ── Project root ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()

# ── Folders ───────────────────────────────────────────────────────────────────
OUTPUT_DIR = ROOT / "output"   # Generated Instagram cards
DATA_DIR   = ROOT / "data"     # Excel tracker
FONT_DIR   = ROOT / "fonts"    # Poppins fonts (auto-downloaded on first run)

# ── Poppins font auto-download ────────────────────────────────────────────────
_POPPINS_BASE  = "https://github.com/google/fonts/raw/main/ofl/poppins"
_POPPINS_FILES = [
    "Poppins-Bold.ttf",
    "Poppins-Medium.ttf",
    "Poppins-Regular.ttf",
    "Poppins-Light.ttf",
]

def _ensure_fonts():
    FONT_DIR.mkdir(exist_ok=True)
    missing = [f for f in _POPPINS_FILES if not (FONT_DIR / f).exists()]
    if missing:
        print(f"  Downloading {len(missing)} Poppins font(s)...")
        for fname in missing:
            try:
                urllib.request.urlretrieve(f"{_POPPINS_BASE}/{fname}", FONT_DIR / fname)
                print(f"  ✓ {fname}")
            except Exception as e:
                print(f"  ✗ Failed to download {fname}: {e}")

_ensure_fonts()

# ── Files ─────────────────────────────────────────────────────────────────────
TRACKER_PATH = DATA_DIR / "f1jobs_tracker.xlsx"

# ── Job API keys (set in .env) ────────────────────────────────────────────────
RAPIDAPI_KEY   = os.getenv("RAPIDAPI_KEY",   "")  # JSearch via RapidAPI
ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID",  "")  # Adzuna free API
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")

# ── Instagram (set in .env — run setup_ig_token.py to populate) ───────────────
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
IG_ACCOUNT_ID   = os.getenv("IG_ACCOUNT_ID",   "")

# ── Cloudinary (image hosting for Instagram Graph API) ───────────────────────
CLOUDINARY_CLOUD_NAME    = os.getenv("CLOUDINARY_CLOUD_NAME",    "qvinwyy0")
CLOUDINARY_UPLOAD_PRESET = os.getenv("CLOUDINARY_UPLOAD_PRESET", "f1jobs")

# ── Google Sheets (set in .env after running sync_to_sheets.py) ───────────────
GOOGLE_SHEET_ID  = os.getenv("GOOGLE_SHEET_ID",  "")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL", "")

# ── Brand ─────────────────────────────────────────────────────────────────────
BRAND_NAME   = "f1jobs"
BRAND_HANDLE = "@f1jobs"
BRAND_TAG    = "F-1 & H-1B Jobs · USA"

# ── Pipeline settings ─────────────────────────────────────────────────────────
JOBS_PER_DAY      = 25  # Total jobs fetched daily
JOBS_PER_CAROUSEL = 5   # Jobs per Instagram carousel
CAROUSELS_PER_DAY = 5   # = JOBS_PER_DAY / JOBS_PER_CAROUSEL

# ── Ensure output & data dirs exist ───────────────────────────────────────────
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
