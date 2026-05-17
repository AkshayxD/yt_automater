"""
Background Video Downloader for YouTube Shorts Bot
Downloads free, license-safe vertical videos from Pixabay.
These are used as background footage behind the narration.

All videos are from Pixabay (Pixabay License: free for commercial use, no attribution required).

Run this once to populate the assets/ folder with variety:
    python download_backgrounds.py
"""
import os
import sys
import requests
import time

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ASSETS_DIR = "assets"

# Curated from Pixabay — handpicked for maximum viewer retention:
# 
# WHY these work:
# - Satisfying/mesmerizing visuals keep eyes GLUED to the screen
# - Non-distracting — they complement narration, don't compete with it
# - Loopable — seamless enough that viewers don't notice the background
# - Vertical-friendly — either vertical or easily croppable
#
# Categories:
# 1. Abstract/neon (hypnotic patterns, keeps eyes moving)
# 2. Night city/rain (atmospheric, sets dramatic mood for stories)
# 3. Space/cosmic (epic feel for dramatic reveals)
# 4. Satisfying flows (universally engaging)

PIXABAY_VIDEOS = [
    # --- ABSTRACT / NEON (best for general stories) ---
    {
        "name": "bg_spiral_tunnel.mp4",
        "url": "https://cdn.pixabay.com/video/2025/03/26/267874_large.mp4",
        "description": "Hypnotic black & white spiral tunnel — mesmerizing optical illusion"
    },
    {
        "name": "bg_retro_grid.mp4",
        "url": "https://cdn.pixabay.com/video/2023/10/24/186372-877727711_large.mp4",
        "description": "Synthwave neon grid tunnel — classic viral Shorts background"
    },
    {
        "name": "bg_neon_circles.mp4",
        "url": "https://cdn.pixabay.com/video/2026/04/11/345863_large.mp4",
        "description": "Glowing blue/purple expanding circles — trippy and satisfying"
    },
    {
        "name": "bg_kaleidoscope.mp4",
        "url": "https://cdn.pixabay.com/video/2025/06/12/285436_large.mp4",
        "description": "Blue and gold mandala kaleidoscope — calming yet captivating"
    },
    {
        "name": "bg_orange_vortex.mp4",
        "url": "https://cdn.pixabay.com/video/2026/03/28/343071_large.mp4",
        "description": "Cosmic orange vortex — intense, perfect for dramatic stories"
    },
    # --- SPACE / COSMIC (dramatic stories, revenge, karma) ---
    {
        "name": "bg_space_nebula.mp4",
        "url": "https://cdn.pixabay.com/video/2026/05/01/350006_large.mp4",
        "description": "Swirling space nebula — epic cinematic feel"
    },
    {
        "name": "bg_neon_particles.mp4",
        "url": "https://cdn.pixabay.com/video/2026/04/09/345605_large.mp4",
        "description": "Glowing particles drifting in deep space — dreamy and immersive"
    },
    # --- NIGHT CITY / RAIN (moody stories, confessions) ---
    {
        "name": "bg_aerial_highway.mp4",
        "url": "https://cdn.pixabay.com/video/2024/03/15/204326-923959262_large.mp4",
        "description": "Aerial night highway curves — atmospheric and cinematic"
    },
    # --- SATISFYING FLOWS (universal appeal) ---
    {
        "name": "bg_satisfying_colors.mp4",
        "url": "https://cdn.pixabay.com/video/2026/02/18/335341_large.mp4",
        "description": "Flowing satisfying color gradients — universally engaging"
    },
    {
        "name": "bg_satisfying_flow.mp4",
        "url": "https://cdn.pixabay.com/video/2025/03/27/267964_large.mp4",
        "description": "Smooth satisfying fluid motion — keeps eyes glued"
    },
]


def download_video(url, output_path, description=""):
    """Downloads a video file with progress indication."""
    print(f"  Downloading: {os.path.basename(output_path)}")
    if description:
        print(f"    ({description})")

    try:
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        mb_down = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        print(f"\r    {mb_down:.1f}/{mb_total:.1f} MB ({pct:.0f}%)", end="", flush=True)

        print(f"\r    Done! ({downloaded / (1024*1024):.1f} MB)              ")
        return True

    except requests.RequestException as e:
        print(f"\n    Failed: {e}")
        # Clean up partial file
        if os.path.exists(output_path):
            os.remove(output_path)
        return False


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    print("=" * 60)
    print("Background Video Downloader")
    print(f"Downloading {len(PIXABAY_VIDEOS)} mesmerizing backgrounds...")
    print("Source: Pixabay (free for commercial use)")
    print("=" * 60 + "\n")

    successful = 0
    skipped = 0

    for i, video in enumerate(PIXABAY_VIDEOS, 1):
        output_path = os.path.join(ASSETS_DIR, video["name"])

        # Skip if already downloaded
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100_000:
            print(f"  [{i}/{len(PIXABAY_VIDEOS)}] Already exists: {video['name']}")
            skipped += 1
            continue

        print(f"\n  [{i}/{len(PIXABAY_VIDEOS)}]")
        if download_video(video["url"], output_path, video["description"]):
            successful += 1
        else:
            print(f"    Skipping {video['name']} due to download failure")

        # Small delay between downloads
        if i < len(PIXABAY_VIDEOS):
            time.sleep(0.5)

    print(f"\n{'=' * 60}")
    print(f"Done! Downloaded: {successful} | Skipped: {skipped} | "
          f"Failed: {len(PIXABAY_VIDEOS) - successful - skipped}")

    # List all background videos now available
    all_bg = [f for f in os.listdir(ASSETS_DIR)
              if f.lower().endswith(('.mp4', '.webm', '.mov'))]
    total_mb = sum(os.path.getsize(os.path.join(ASSETS_DIR, f)) for f in all_bg) / (1024 * 1024)
    print(f"\nTotal background videos in assets/: {len(all_bg)} ({total_mb:.0f} MB)")
    for f in sorted(all_bg):
        size_mb = os.path.getsize(os.path.join(ASSETS_DIR, f)) / (1024 * 1024)
        print(f"  - {f} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
