import os
import shutil
import time
from scraper import get_reddit_story
from audio_gen import generate_audio_and_subs
from video_gen import create_video
from youtube_api import get_authenticated_service
from uploader import upload_video

# Directories
VIDEOS_DIR = "videos_to_upload"
UPLOADED_DIR = "uploaded_videos"
TEMP_DIR = "temp"
ASSETS_DIR = "assets"

def setup_directories():
    """Creates necessary directories if they don't exist."""
    for d in [VIDEOS_DIR, UPLOADED_DIR, TEMP_DIR, ASSETS_DIR]:
        os.makedirs(d, exist_ok=True)

def create_and_upload_viral_short():
    """The main pipeline: generate script -> voice -> video -> upload."""
    setup_directories()
    
    print("\n" + "="*50)
    print("STARTING VIRAL SHORT GENERATION PIPELINE")
    print("="*50 + "\n")
    
    # 1. Generate / Fetch Script
    title, body = get_reddit_story()
    print(f"\n[1] Fetched Script:\nTitle: {title}\nLength: {len(body.split())} words")
    
    # Safety check on length: YouTube Shorts MUST be under 60 seconds.
    script_text = f"{title}. {body}"
    # The scraper already filters for < 155 words. 
    # At +15% TTS speed, 160 words easily fits under 60 seconds.
    if len(script_text.split()) > 175:
        print("Warning: Script is unusually long. It might exceed the 60-second limit for Shorts.")
        # Try to cut at the last sentence boundary
        script_text = script_text[:850]
        last_period = script_text.rfind('.')
        if last_period > 0:
            script_text = script_text[:last_period+1]
        
    # 2. Generate Audio and Subtitles
    print("\n[2] Generating Voiceover and Subtitles...")
    audio_file = os.path.join(TEMP_DIR, "audio.mp3")
    subs_file = os.path.join(TEMP_DIR, "subs.vtt")
    
    mp3_path, vtt_path = generate_audio_and_subs(script_text, audio_file, subs_file)
    
    if not mp3_path or not vtt_path:
        print("Failed to generate audio. Aborting.")
        return
        
    # 3. Assemble Video
    print("\n[3] Assembling Video...")
    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    safe_title_underscored = safe_title.replace(" ", "_")
    final_video_path = os.path.join(VIDEOS_DIR, f"{safe_title_underscored}.mp4")
    
    # Using a background video if present, otherwise it generates black background
    bg_video = os.path.join(ASSETS_DIR, "background.mp4")
    
    try:
        rendered_video = create_video(mp3_path, vtt_path, background_path=bg_video, output_path=final_video_path)
    except Exception as e:
        print(f"Error during video generation: {e}")
        return
        
    print(f"\nVideo successfully generated: {rendered_video}")
    
    # 4. Upload to YouTube
    print("\n[4] Uploading to YouTube...")
    try:
        youtube_client = get_authenticated_service()
    except Exception as e:
        print(f"Failed to authenticate with YouTube API: {e}")
        print(f"Your video is saved at {rendered_video}. You can upload it manually.")
        return
        
    full_title = f"{safe_title[:85]} #shorts #story"
    description = f"{script_text[:1000]}\n\n#shorts #reddit #story #viral"
    tags = ["shorts", "reddit", "story", "trueoffmychest", "viral"]
    
    try:
        upload_video(
            youtube=youtube_client,
            file_path=rendered_video,
            title=full_title,
            description=description,
            category_id="22", # People & Blogs
            keywords=tags,
            privacy_status="private" # Keep private until reviewed
        )
        
        # Move to uploaded
        dest_path = os.path.join(UPLOADED_DIR, os.path.basename(rendered_video))
        shutil.move(rendered_video, dest_path)
        print(f"Moved video to {UPLOADED_DIR}/")
        
    except Exception as e:
        print(f"Failed to upload video: {e}")
        
    print("\n" + "="*50)
    print("PIPELINE COMPLETE")
    print("="*50 + "\n")

if __name__ == "__main__":
    create_and_upload_viral_short()
