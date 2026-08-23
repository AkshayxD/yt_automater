"""
Content Asset Downloader — Sets up asset directories for all content types.

Creates dedicated background and music directories for each content type:
- assets/wyr_bg/           (Would You Rather backgrounds)
- assets/fake_text_bg/     (Fake Text Message backgrounds)
- assets/dark_psych_bg/    (Dark Psychology backgrounds)
- assets/true_crime_bg/    (True Crime backgrounds)
- assets/true_crime_music/ (Eerie ambient music for True Crime)

All content types gracefully fallback to the shared assets/ pool
if their type-specific directories are empty.

Due to strict CDN protections on Pixabay and Mixkit, direct hotlinking
to MP4 files without an API key is no longer supported. The pipeline
is fully designed to fallback to existing assets/ backgrounds.

To add custom backgrounds for each content type:
1. Go to pexels.com, pixabay.com, or mixkit.co
2. Search for the suggested keywords below
3. Download the free MP4s
4. Place them in the appropriate directory
"""
import os

# Directory mapping with search suggestions
CONTENT_DIRS = {
    "assets/wyr_bg": {
        "description": "Would You Rather backgrounds",
        "search_keywords": "colorful abstract background, neon lights, quiz show background, vibrant particles",
    },
    "assets/fake_text_bg": {
        "description": "Fake Text Message backgrounds",
        "search_keywords": "dark gradient background, phone screen blur, city lights bokeh, dark abstract",
    },
    "assets/dark_psych_bg": {
        "description": "Dark Psychology backgrounds",
        "search_keywords": "dark mysterious background, neural network, brain visualization, dark abstract particles",
    },
    "assets/true_crime_bg": {
        "description": "True Crime / Horror backgrounds",
        "search_keywords": "dark forest, foggy night, abandoned building, horror atmosphere, dark rain",
    },
    "assets/true_crime_music": {
        "description": "True Crime / Horror ambient music",
        "search_keywords": "dark ambient, horror atmosphere, suspense music, creepy background",
    },
    "assets/number_facts_bg": {
        "description": "Number Facts backgrounds",
        "search_keywords": "space galaxy, stars universe, cosmic background, nebula, planets space",
    },
    "assets/history_bg": {
        "description": "Historical Facts backgrounds",
        "search_keywords": "old film grain, vintage paper, historical documents, ancient architecture, sepia tone",
    },
}


def main():
    print("=" * 60)
    print("\U0001F3AC Content Asset Setup — All Content Types")
    print("=" * 60)

    for dir_path, info in CONTENT_DIRS.items():
        os.makedirs(dir_path, exist_ok=True)
        existing = [f for f in os.listdir(dir_path)
                    if f.lower().endswith(('.mp4', '.webm', '.mov', '.mp3'))]
        status = f"{len(existing)} files" if existing else "empty (will use shared assets/)"
        print(f"\n  \u2714 {dir_path}/")
        print(f"    {info['description']}")
        print(f"    Status: {status}")
        print(f"    Search: \"{info['search_keywords']}\"")

    print(f"\n{'=' * 60}")
    print("\u26A0\uFE0F  NOTE: Automatic downloads from Pixabay CDN are blocked.")
    print("  All content types will safely fallback to existing backgrounds")
    print("  in assets/ if their specific directories are empty.")
    print("")
    print("  To add custom backgrounds, download MP4s from:")
    print("    \u2192 pexels.com (free, no attribution)")
    print("    \u2192 pixabay.com (free, Pixabay License)")
    print("    \u2192 mixkit.co (free stock video)")
    print("  and place them in the appropriate directory above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
