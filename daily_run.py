"""
f1jobs — Daily Runner
Full end-to-end pipeline: fetch → excel → carousels → sheets → instagram.

Usage:
  python daily_run.py                    # full run: all 25 jobs, 5 carousels, post all
  python daily_run.py --carousel 1       # single carousel only
  python daily_run.py --jobs 25          # explicit job count
  python daily_run.py --no-sheets        # skip Google Sheets sync
  python daily_run.py --no-post          # skip Instagram posting
  python daily_run.py --dry-run          # generate images but don't post or sync
"""
from __future__ import annotations

import os, argparse
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="f1jobs pipeline")
    parser.add_argument("--jobs",      type=int, default=None,
                        help="Total jobs to fetch (default: 5 per carousel, 25 for all)")
    parser.add_argument("--carousel",  type=int, default=None, choices=range(1, 6),
                        help="Run a single carousel (1-5)")
    parser.add_argument("--no-sheets", action="store_true",
                        help="Skip Google Sheets sync")
    parser.add_argument("--no-post",   action="store_true",
                        help="Skip Instagram posting")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Generate images only — no posting or syncing")
    args = parser.parse_args()

    if args.dry_run:
        args.no_sheets = True
        args.no_post   = True

    single_mode  = args.carousel is not None
    carousel_num = args.carousel or 1
    n            = args.jobs if args.jobs else (5 if single_mode else 25)
    n_carousels  = 1 if single_mode else (n // 5)

    print("\n" + "="*60)
    print(f"  f1jobs — {datetime.now().strftime('%A, %b %d %Y  %H:%M')}")
    if single_mode:
        print(f"  Mode: Carousel {carousel_num}/5  ({n} jobs)")
    else:
        print(f"  Mode: Full run  ({n} jobs → {n_carousels} carousels)")
    if args.dry_run:
        print("  [DRY RUN — no posting or syncing]")
    print("="*60)

    # ── Step 1: Fetch ──────────────────────────────────────────────────────────
    print("\n[1/5]  Fetching H-1B jobs...")
    from fetcher import get_daily_jobs
    jobs = get_daily_jobs(n)

    # ── Step 2: Excel tracker ──────────────────────────────────────────────────
    print("\n[2/5]  Updating Excel tracker...")
    from sheet_builder import create_or_open_tracker, append_jobs, mark_cards_generated, save_tracker
    wb    = create_or_open_tracker()
    added = append_jobs(jobs, wb)

    # ── Step 3: Generate carousels ─────────────────────────────────────────────
    print("\n[3/5]  Generating carousel(s)...")
    from carousel_generator import generate_daily_carousel, generate_all_carousels

    if single_mode:
        paths     = generate_daily_carousel(jobs[:5], carousel_num=carousel_num)
        all_paths = [paths]
    else:
        all_paths = generate_all_carousels(jobs)

    mark_cards_generated(jobs, wb)
    save_tracker(wb)

    # ── Step 4: Google Sheets sync ─────────────────────────────────────────────
    sheet_url = os.getenv("GOOGLE_SHEET_URL", "")
    if not args.no_sheets:
        print("\n[4/5]  Syncing to Google Sheets...")
        try:
            from sync_to_sheets import sync
            sheet_url = sync() or sheet_url
        except Exception as e:
            print(f"  ⚠  Sheets sync failed (non-fatal): {e}")
    else:
        print("\n[4/5]  Skipping Google Sheets sync")

    # ── Step 5: Post to Instagram ──────────────────────────────────────────────
    posted = []
    if not args.no_post:
        print("\n[5/5]  Posting to Instagram...")
        from poster import post_carousel
        carousels_to_post = [carousel_num] if single_mode else list(range(1, n_carousels + 1))
        for c_num in carousels_to_post:
            print(f"\n  ── Carousel {c_num}/5 ──")
            try:
                post_carousel(c_num, dry_run=False)
                posted.append(c_num)
            except Exception as e:
                print(f"  ✗  Failed to post carousel {c_num}: {e}")
    else:
        print("\n[5/5]  Skipping Instagram posting")

    # ── Summary ────────────────────────────────────────────────────────────────
    total_cards = sum(len(p) for p in all_paths)
    print("\n" + "="*60)
    print("  ✓  DONE")
    print(f"  Jobs fetched      : {len(jobs)}")
    print(f"  New rows in sheet : {added}")
    print(f"  Carousels made    : {len(all_paths)}")
    print(f"  Cards generated   : {total_cards}")
    print(f"  IG carousels posted: {posted if posted else 'none'}")
    print(f"  Google Sheet      : {sheet_url or '(not synced)'}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
