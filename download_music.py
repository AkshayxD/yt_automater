"""
Download free CC0 background music tracks for Reddit narration Shorts.

These tracks are from Pixabay (CC0 license — free for commercial use, no attribution needed).
They are ambient/suspenseful tracks at a low tempo that sit well under a voiceover.

Usage:
    python download_music.py

This will download ~8 tracks into assets/music/.
You can add more manually: go to pixabay.com/music, filter by "Suspenseful" or "Cinematic",
download the MP3, and drop it in assets/music/.
"""
import os
import sys
import urllib.request

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

MUSIC_DIR = os.path.join("assets", "music")

# Note: Pixabay requires visiting their site to download (CDN links are protected).
# The tracks below use Freesound.org CC0 links which allow direct download.
# After running this script, also manually grab tracks from:
#   → https://pixabay.com/music/ (search "suspenseful", "cinematic", "dark ambient")
#   → https://studio.youtube.com → Audio Library → "Ambient" + "Dark"
#   → https://mixkit.co/free-stock-music/ → "Cinematic"
# Save all MP3s to assets/music/ — the pipeline picks a random one per video.

CC0_TRACKS = [
    {
        "name": "mysterious_cinematic.mp3",
        "url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
        "mood": "Mysterious cinematic — works for any drama story"
    },
]

# YouTube Audio Library tracks (download manually from studio.youtube.com/channel/UC.../music)
# These are 100% safe for monetization. Suggested searches:
#   - "Ambient" > "Dark" filter
#   - "Cinematic" > "Dramatic" filter
#   - Artist: Kevin MacLeod (all CC BY)
MANUAL_INSTRUCTIONS = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALSO: Get more tracks from these free sources:

1. Pixabay Music (CC0, no attribution needed):
   → https://pixabay.com/music/
   → Filter: "Suspenseful" or "Cinematic" or "Dark"
   → Download MP3 → drop in assets/music/

2. YouTube Audio Library (100% monetization-safe):
   → studio.youtube.com → Audio Library
   → Filter: "Ambient" + "Dark"
   → Download → drop in assets/music/

3. Mixkit (CC0):
   → https://mixkit.co/free-stock-music/
   → Category: "Cinematic" → download MP3

Target: 8-10 different tracks so each video uses a different one.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def download_tracks():
    os.makedirs(MUSIC_DIR, exist_ok=True)

    print("Downloading CC0 background music tracks...")
    print(f"Saving to: {os.path.abspath(MUSIC_DIR)}\n")

    downloaded = 0
    failed = 0

    for track in CC0_TRACKS:
        dest = os.path.join(MUSIC_DIR, track["name"])
        if os.path.exists(dest):
            print(f"  ✅ Already exists: {track['name']}")
            downloaded += 1
            continue

        print(f"  Downloading: {track['name']} ({track['mood']})")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            req = urllib.request.Request(track["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
            with open(dest, 'wb') as f:
                f.write(data)
            size_kb = len(data) // 1024
            print(f"  ✅ Downloaded: {track['name']} ({size_kb}KB)")
            downloaded += 1
        except Exception as e:
            print(f"  ❌ Failed: {track['name']} — {e}")
            print(f"     → Manually download from: {track['url']}")
            failed += 1

    print(f"\n{'─' * 50}")
    print(f"Done: {downloaded} tracks ready, {failed} failed")

    # List what's in the folder
    existing = [f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')]
    if existing:
        print(f"\nTracks available ({len(existing)}):")
        for f in existing:
            size = os.path.getsize(os.path.join(MUSIC_DIR, f)) // 1024
            print(f"  • {f} ({size}KB)")
    else:
        print("\n⚠️ No tracks downloaded. Add MP3 files manually to assets/music/")

    print(MANUAL_INSTRUCTIONS)


if __name__ == "__main__":
    download_tracks()
