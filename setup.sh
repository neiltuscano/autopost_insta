#!/bin/bash
# f1jobs — First-time Mac setup
# Run once from the project folder: bash setup.sh

echo ""
echo "  f1jobs setup"
echo "  ─────────────────────────────────"

# 1. Install Python dependencies
echo ""
echo "  [1/4] Installing Python packages..."
pip3 install -r requirements.txt
echo "  ✓ Done"

# 2. Set up .env
echo ""
echo "  [2/4] Setting up .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  ✓ .env created — open it and add your API keys"
else
    echo "  ✓ .env already exists"
fi

# 3. Instagram token
echo ""
echo "  [3/4] Instagram setup..."
echo "  To connect Instagram, run:"
echo "    python3 setup_ig_token.py --paste-token"
echo "  (You'll need a long-lived Instagram access token from Meta.)"

# 4. Google Sheets setup
echo ""
echo "  [4/4] Google Sheets setup..."
echo "  Requirements:"
echo "    a) Create a Google Sheet and share it with your service account"
echo "       (f1jobs-sheets@f1jobs-506321.iam.gserviceaccount.com) as Editor"
echo "    b) Copy the Sheet ID from the URL and add to .env:"
echo "       GOOGLE_SHEET_ID=<your_sheet_id>"
echo "    c) Place f1jobs-sheets-key.json in this folder"
echo "  Then test with: python3 sync_to_sheets.py --dry-run"

echo ""
echo "  ─────────────────────────────────"
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "    1. Fill in your API keys in .env"
echo "    2. Run:  python3 setup_ig_token.py --paste-token"
echo "    3. Run:  python3 daily_run.py --dry-run   (test pipeline)"
echo "    4. Run:  python3 daily_run.py              (full run)"
echo ""
