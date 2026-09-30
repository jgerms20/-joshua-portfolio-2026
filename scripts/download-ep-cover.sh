#!/bin/bash
# Run this locally to download the Eclectic Polymath cover art from Spotify
# Usage: SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... bash scripts/download-ep-cover.sh
# Credentials come from the environment only; never hardcode them here.

CLIENT_ID="${SPOTIFY_CLIENT_ID:?Set SPOTIFY_CLIENT_ID (from developer.spotify.com/dashboard)}"
CLIENT_SECRET="${SPOTIFY_CLIENT_SECRET:?Set SPOTIFY_CLIENT_SECRET (never commit it)}"
SHOW_ID="3dlagzJ0jiWLTB9mF3y069"
OUT="Images/Podcasts/eclectic-polymath-cover.jpg"

TOKEN=$(curl -s -X POST "https://accounts.spotify.com/api/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -u "${CLIENT_ID}:${CLIENT_SECRET}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

IMAGE_URL=$(curl -s "https://api.spotify.com/v1/shows/${SHOW_ID}" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -c "import sys,json; imgs=json.load(sys.stdin)['images']; print(sorted(imgs,key=lambda x:-x['width'])[0]['url'])")

echo "Downloading cover from: $IMAGE_URL"
curl -s -L "$IMAGE_URL" -o "$OUT"
echo "Saved to $OUT"
