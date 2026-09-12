#!/bin/bash
# f1jobs — Unified runner
# Called by Mac LaunchAgents with the carousel number (1-5).
#
# Schedule:
#   Carousel 1 — 8:00 AM  → fetches 25 jobs, generates all 5 carousels,
#                            syncs to Google Sheets, posts carousel 1
#   Carousel 2 — 10:30 AM → posts carousel 2 (images already generated)
#   Carousel 3 —  1:00 PM → posts carousel 3
#   Carousel 4 —  3:30 PM → posts carousel 4
#   Carousel 5 —  6:00 PM → posts carousel 5

CAROUSEL_NUM="${1:-1}"
PROJECT_DIR="/Users/neil/Projects/f1jobs"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/run_$(date +%Y-%m-%d)_carousel${CAROUSEL_NUM}.log"

mkdir -p "$LOG_DIR"

echo "================================================" >> "$LOG_FILE"
echo "  f1jobs Carousel ${CAROUSEL_NUM}/5 — $(date '+%A %b %d %Y %H:%M:%S')" >> "$LOG_FILE"
echo "================================================" >> "$LOG_FILE"

# Load .env
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs) 2>/dev/null
fi

# Find Python
PYTHON=""
for p in \
    /Users/neil/opt/anaconda3/bin/python3 \
    /Users/neil/anaconda3/bin/python3 \
    /usr/local/bin/python3 \
    /opt/homebrew/bin/python3 \
    /usr/bin/python3; do
    if [ -x "$p" ]; then
        PYTHON="$p"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: python3 not found." >> "$LOG_FILE"
    osascript -e "display notification \"python3 not found\" with title \"f1jobs ✗ Error\"" 2>/dev/null
    exit 1
fi

cd "$PROJECT_DIR"

# ── Helper: run full pipeline (fetch + generate all 5 + sync) ─────────────────
run_pipeline() {
    # Atomic lock: prevents two LaunchAgent firings from running the pipeline
    # concurrently (e.g. a late carousel-1 wake racing with carousel-2's self-heal).
    LOCK_DIR="$PROJECT_DIR/.pipeline_lock"
    if ! mkdir "$LOCK_DIR" 2>/dev/null; then
        echo "  ⚠  Pipeline already running (lock exists) — waiting up to 30 min..." >> "$LOG_FILE"
        WAITED=0
        while [ -d "$LOCK_DIR" ] && [ $WAITED -lt 1800 ]; do
            sleep 30
            WAITED=$(( WAITED + 30 ))
        done
        if [ -d "$LOCK_DIR" ]; then
            echo "  ⚠  Lock still held after 30 min — breaking stale lock and skipping pipeline" >> "$LOG_FILE"
            rm -rf "$LOCK_DIR"
            return 0  # other pipeline likely still running; let poster use whatever images exist
        fi
        echo "  ✓ Lock released after ${WAITED}s — images should now be ready" >> "$LOG_FILE"
        return 0  # other pipeline finished; skip re-running it
    fi

    echo "  [pipeline] Fetching jobs, generating all 5 carousels, syncing to Sheets..." >> "$LOG_FILE"
    "$PYTHON" -u daily_run.py --no-post >> "$LOG_FILE" 2>&1
    local code=$?
    rm -rf "$LOCK_DIR"
    if [ $code -ne 0 ]; then
        echo "  ✗ Pipeline failed (exit $code)" >> "$LOG_FILE"
        osascript -e "display notification \"Pipeline failed — check logs/\" with title \"f1jobs ✗\"" 2>/dev/null
        exit $code
    fi
    echo "  ✓ All 5 carousels generated + Sheets synced" >> "$LOG_FILE"
}

# ── Carousel 1: always runs the full pipeline ─────────────────────────────────
if [ "$CAROUSEL_NUM" = "1" ]; then
    echo "  [1/2] Running full pipeline (fetch, generate, sync to Sheets)..." >> "$LOG_FILE"
    run_pipeline
fi

# ── Carousels 2-5: self-healing — run pipeline if images are missing ──────────
if [ "$CAROUSEL_NUM" != "1" ]; then
    PREFIX="carousel_$(printf '%02d' $CAROUSEL_NUM)_"
    IMAGE_COUNT=$(ls "$PROJECT_DIR/output/${PREFIX}"*.png 2>/dev/null | wc -l | tr -d ' ')
    if [ "$IMAGE_COUNT" -lt 2 ]; then
        echo "  ⚠  No images found for carousel $CAROUSEL_NUM (carousel 1 may have been skipped)" >> "$LOG_FILE"
        echo "  [1/2] Running full pipeline as fallback..." >> "$LOG_FILE"
        run_pipeline
    else
        echo "  [1/2] Images ready ($IMAGE_COUNT found) — skipping generation" >> "$LOG_FILE"
    fi
fi

# ── All carousels: post to Instagram ──────────────────────────────────────────
echo "  [2/2] Posting carousel ${CAROUSEL_NUM}/5 to Instagram..." >> "$LOG_FILE"
"$PYTHON" poster.py --carousel "$CAROUSEL_NUM" >> "$LOG_FILE" 2>&1
POST_CODE=$?

if [ $POST_CODE -eq 0 ]; then
    echo "  ✓ Carousel ${CAROUSEL_NUM}/5 posted to Instagram!" >> "$LOG_FILE"
    osascript -e "display notification \"Carousel ${CAROUSEL_NUM}/5 — live on Instagram!\" with title \"f1jobs ✓\"" 2>/dev/null
else
    echo "  ✗ Instagram post failed (exit $POST_CODE)" >> "$LOG_FILE"
    osascript -e "display notification \"Carousel ${CAROUSEL_NUM}/5 — post failed, check logs/\" with title \"f1jobs ⚠️\"" 2>/dev/null
fi

echo "  Finished: $(date '+%H:%M:%S')" >> "$LOG_FILE"
ls -t "$LOG_DIR"/run_*.log 2>/dev/null | tail -n +31 | xargs rm -f
exit $POST_CODE
