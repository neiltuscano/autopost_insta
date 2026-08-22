#!/usr/bin/env python3
"""
Instagram token setup for f1jobs.

Two modes:
  python3 setup_ig_token.py                # exchange short-lived token (needs App Secret)
  python3 setup_ig_token.py --paste-token  # paste a long-lived token directly (no App Secret)
"""

import sys
import os
import urllib.request
import urllib.parse
import json
import re
import getpass

ENV_PATH      = os.path.expanduser("~/Projects/f1jobs/.env")
APP_ID        = "1049741537818655"
IG_ACCOUNT_ID = "17841439487853370"

def exchange_token(app_id, app_secret, short_token):
    params = urllib.parse.urlencode({
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token,
    })
    url = f"https://graph.facebook.com/v26.0/oauth/access_token?{params}"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
            msg = err.get("error", {}).get("message", body)
            code = err.get("error", {}).get("code", "?")
            raise RuntimeError(f"API error {code}: {msg}")
        except (json.JSONDecodeError, AttributeError):
            raise RuntimeError(f"HTTP {e.code}: {body[:300]}")
    return data.get("access_token"), data.get("expires_in")

def update_env(env_path, key, value):
    """Insert or replace a key=value line in the .env file."""
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            content = f.read()
    else:
        content = ""
    pattern = rf"^{re.escape(key)}=.*$"
    new_line = f"{key}={value}"
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content = content.rstrip("\n") + "\n" + new_line + "\n"
    with open(env_path, "w") as f:
        f.write(content)

def main():
    paste_mode = "--paste-token" in sys.argv

    print("=== f1jobs Instagram token setup ===\n")

    if paste_mode:
        print("Paste the long-lived token from the Meta Access Token Debugger.")
        print("(The green token shown after clicking 'Extend Access Token')\n")
        long_token = getpass.getpass("Paste long-lived token (hidden): ").strip()
        if not long_token or not long_token.startswith("EAA"):
            print("❌  That doesn't look like a valid token (should start with EAA).")
            sys.exit(1)
        expires_note = "~60 days"
    else:
        print("You need two things from your browser:\n"
              "  1. App Secret  (Meta Developer Portal → App Settings → Basic)\n"
              "  2. Short-lived User Access Token  (Graph API Explorer)\n")
        app_secret  = getpass.getpass("Paste App Secret (hidden): ").strip()
        short_token = getpass.getpass("Paste short-lived token (hidden): ").strip()
        if not app_secret or not short_token:
            print("❌  Both values are required.")
            sys.exit(1)
        print("\nExchanging token …")
        try:
            long_token, expires_in = exchange_token(APP_ID, app_secret, short_token)
        except Exception as e:
            print(f"❌  Token exchange failed: {e}")
            sys.exit(1)
        if not long_token:
            print("❌  No access_token in response.")
            sys.exit(1)
        days = int(expires_in) // 86400 if expires_in else "unknown"
        expires_note = f"~{days} days"

    update_env(ENV_PATH, "IG_ACCESS_TOKEN", long_token)
    update_env(ENV_PATH, "IG_ACCOUNT_ID",   IG_ACCOUNT_ID)
    print(f"\n✓  Long-lived token written to {ENV_PATH}  (expires in {expires_note})")
    print("✓  IG_ACCOUNT_ID=17841439487853370 written")
    print("\nDone! Your poster.py is now wired up for Instagram posting.")

if __name__ == "__main__":
    main()
