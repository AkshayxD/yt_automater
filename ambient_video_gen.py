"""
Ambient Video Generator

Generates 3-hour long "TV Wallpaper" / Sleep videos (e.g., Rain sounds, space ambiance).
Uses a static AI generated image or black screen, and loops a short audio file for 3 hours.
Uses raw ffmpeg for extreme speed and low memory usage (MoviePy would crash on 3hr videos).
"""
import os
import sys
import random
import urllib.parse
import urllib.request
import subprocess
from datetime import datetime

TEMP_DIR = "temp"
ASSETS_DIR = "assets"
VIDEOS_DIR = "videos_to_upload"

# 3 Hours in seconds
DURATION_SEC = 10800 

AMBIENT_THEMES = [
    {"name": "Heavy Rain and Thunder", "prompt": "A dark, moody cinematic view of rain pouring down a window in a cozy room at night", "audio_keyword": "rain"},
    {"name": "Deep Space Ambience", "prompt": "A breathtaking cinematic view of a glowing nebula in deep space", "audio_keyword": "space"},
    {"name": "Cozy Fireplace", "prompt": "A warm, crackling fireplace in a dark, cozy cabin", "audio_keyword": "fire"},
    {"name": "Ocean Waves", "prompt": "A peaceful dark beach at night with glowing bioluminescent waves", "audio_keyword": "ocean"},
    {"name": "Pure Black Screen (Brown Noise)", "prompt": "black screen", "audio_keyword": "noise"},
]

def download_ambient_image(prompt):
    if prompt == "black screen":
        # Generate a small black square locally
        img_path = os.path.join(TEMP_DIR, "black.jpg")
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1920x1080", "-frames:v", "1", img_path], capture_output=True)
        return img_path

    safe_prompt = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1920&height=1080&nologo=true"
    image_path = os.path.join(TEMP_DIR, "ambient_bg.jpg")
    try:
        req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(image_path, 'wb') as f:
                f.write(response.read())
        return image_path
    except Exception as e:
        print(f"  ❌ Failed to download AI image: {e}")
        # Fallback to black screen
        img_path = os.path.join(TEMP_DIR, "black.jpg")
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1920x1080", "-frames:v", "1", img_path], capture_output=True)
        return img_path

def generate_ambient_audio():
    # In a real scenario we would download a free sound effect based on the audio_keyword.
    # For now, we will dynamically generate brown noise/pink noise using ffmpeg's lavfi.
    audio_path = os.path.join(TEMP_DIR, "ambient_base.mp3")
    
    # 60 seconds of brown noise (deep relaxing sound)
    print("  🎵 Generating ambient audio loop...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=c=brown:a=0.5", 
        "-t", "60", "-c:a", "libmp3lame", audio_path
    ], capture_output=True)
    return audio_path

def create_ambient_video():
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)

    theme = random.choice(AMBIENT_THEMES)
    print(f"\n  🌙 Generating 3-Hour Ambient Video: {theme['name']}")
    
    # 1. Get visual (Image or Black screen)
    print("  🖼️ Acquiring visual...")
    img_path = download_ambient_image(theme['prompt'])

    # 2. Get audio loop
    audio_path = generate_ambient_audio()

    # 3. Assemble via ffmpeg
    safe_title = theme['name'].replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(VIDEOS_DIR, f"AMBIENT_{safe_title}_{timestamp}.mp4")

    print(f"  🎥 Rendering 3-hour video via ffmpeg (This will be very fast but output a ~150MB file)...")
    
    # ffmpeg command:
    # -loop 1: loop the single image
    # -stream_loop -1: infinitely loop the audio
    # -i img, -i audio
    # -c:v libx264 -tune stillimage (highly optimized for static image, takes almost 0 bytes for video)
    # -c:a aac -b:a 128k
    # -t DURATION
    # -pix_fmt yuv420p (compatibility)
    # -shortest (stop at duration)
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", img_path,
        "-stream_loop", "-1", "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(DURATION_SEC),
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print("  ✅ 3-Hour video rendered successfully!")
        
        return {
            "success": True,
            "title": f"3 HOURS of {theme['name']} for Sleep, Study & Focus",
            "file_path": output_path,
            "theme": theme['name']
        }
    except subprocess.CalledProcessError as e:
        print(f"  ❌ FFmpeg failed: {e.stderr.decode('utf-8', errors='ignore')}")
        return {"success": False}

if __name__ == "__main__":
    create_ambient_video()
