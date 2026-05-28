"""
Inspiration Asset Downloader — Dark cinematic backgrounds.

Due to strict CDN protections (403 Forbidden) on Pixabay and Mixkit,
direct hotlinking to MP4 files without an API key is no longer supported.

However, the pipeline is fully designed to fallback to the existing `assets/`
videos (like bg_aerial_highway.mp4, bg_space_nebula.mp4) if no specific
inspiration backgrounds are found.

To add custom Dark Stoic backgrounds:
1. Go to pexels.com or mixkit.co
2. Search for "dark cinematic background vertical" (stormy clouds, fog, fire)
3. Download the free MP4s
4. Place them in: assets/inspiration_bg/

Music is not natively supported by the current `video_gen.py` pipeline to keep
videos raw and ADHD-friendly (YouTube algorithms often prefer raw voiceover).
"""
import os

INSPIRATION_BG_DIR = os.path.join("assets", "inspiration_bg")

def main():
    print("=" * 60)
    print("🏛️ Inspiration Asset Setup")
    print("=" * 60)
    
    os.makedirs(INSPIRATION_BG_DIR, exist_ok=True)
    
    print("\n✅ Directory structure verified:")
    print(f"  - {os.path.abspath(INSPIRATION_BG_DIR)}")
    
    print("\n⚠️ NOTE: Automatic direct downloads from Pixabay are blocked.")
    print("  The pipeline will safely fallback to existing backgrounds in assets/.")
    print("  If you wish to add custom dark cinematic backgrounds, download them")
    print("  manually from Pexels/Mixkit and place them in the directory above.")
    print("=" * 60)

if __name__ == "__main__":
    main()

