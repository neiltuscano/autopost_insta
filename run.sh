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

# ── Carousel 1: full pipeline (fetch + generate all + sync + post 1) ──────────
if [ "$CAROUSEL_NUM" = "1" ]; then
    echo "  [1/2] Running full pipeline (fetch, generate, sync to Sheets)..." >> "$LOG_FILE"
    "$PYTHON" -u daily_run.py --no-post >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?

    if [ $EXIT_CODE -ne 0 ]; then
        echo "  ✗ Pipeline failed (exit $EXIT_CODE)" >> "$LOG_FILE"
        osascript -e "display notification \"Pipeline failed — check logs/\" with title \"f1jobs ✗\"" 2>/dev/null
        exit $EXIT_CODE
    fi
    echo "  ✓ All 5 carousels generated + Sheets synced" >> "$LOG_FILE"
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
