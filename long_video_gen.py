"""
Generates the long-form video essay with a Ken Burns slideshow using AI generated images.
"""
import os
import sys
import random
import urllib.parse
import urllib.request
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    ColorClip, ImageClip, concatenate_videoclips
)
from moviepy.audio.AudioClip import CompositeAudioClip
from video_gen import parse_srt, group_words_into_chunks, create_subtitle_clips, trim_audio_silence

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
TEMP_DIR = "temp"

def download_ai_image(prompt, idx):
    """
    Downloads an AI generated image based on the prompt.
    For 100% free approach, using pollinations.ai (no API key required).
    Fallback to a color clip if it fails.
    """
    safe_prompt = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1920&height=1080&nologo=true"
    image_path = os.path.join(TEMP_DIR, f"slide_{idx}.jpg")
    try:
        req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(image_path, 'wb') as f:
                f.write(response.read())
        return image_path
    except Exception as e:
        print(f"  ❌ Failed to download AI image for slide {idx}: {e}")
        return None

def apply_ken_burns(image_path, duration):
    """
    Applies a slow zoom in/out or pan effect to an image.
    """
    try:
        clip = ImageClip(image_path).set_duration(duration)
        
        # Randomly choose zoom in or zoom out
        zoom_in = random.choice([True, False])
        if zoom_in:
            def zoom(t):
                return 1.0 + 0.05 * (t / duration)
        else:
            def zoom(t):
                return 1.05 - 0.05 * (t / duration)
                
        clip = clip.resize(zoom)
        clip = clip.set_position(('center', 'center'))
        # Crop to strict 16:9 in case resize goes out of bounds
        clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=VIDEO_WIDTH, height=VIDEO_HEIGHT)
        return clip
    except Exception as e:
        print(f"  ❌ Error applying Ken Burns: {e}")
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(30, 30, 30), duration=duration)

def create_long_video(audio_path, srt_path, visual_prompts, output_path="final_long_video.mp4", content_type="story"):
    print("  Assembling LONG FORM final video...")

    audio = AudioFileClip(audio_path)
    audio = trim_audio_silence(audio)
    audio_duration = audio.duration
    
    # 1. Download images and create slideshow
    print(f"  🖼️ Creating Ken Burns slideshow with {len(visual_prompts)} scenes...")
    scene_duration = audio_duration / max(1, len(visual_prompts))
    
    slide_clips = []
    for idx, prompt in enumerate(visual_prompts):
        print(f"    Downloading slide {idx+1}/{len(visual_prompts)}...")
        img_path = download_ai_image(prompt, idx)
        if img_path:
            slide = apply_ken_burns(img_path, scene_duration)
        else:
            slide = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(20, 20, 20), duration=scene_duration)
        slide_clips.append(slide.crossfadein(1.0))
        
    if slide_clips:
        bg_clip = concatenate_videoclips(slide_clips, method="compose")
        # Ensure it matches exact audio duration
        bg_clip = bg_clip.set_duration(audio_duration)
    else:
        bg_clip = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(20, 20, 20), duration=audio_duration)

    # 2. Add Ambient Music
    import glob
    music_files = glob.glob(os.path.join('assets', 'music', '*.mp3'))
    if music_files:
        music_path = random.choice(music_files)
        try:
            music = AudioFileClip(music_path)
            if music.duration < audio_duration:
                from moviepy.audio.fx.all import audio_loop
                music = music.fx(audio_loop, duration=audio_duration)
            else:
                music = music.subclip(0, audio_duration)
            music = music.volumex(0.10) # 10% volume for ambient essay style
            mixed_audio = CompositeAudioClip([audio, music])
        except:
            mixed_audio = audio
    else:
        mixed_audio = audio
        
    bg_clip = bg_clip.set_audio(mixed_audio)

    # 3. Add Subtitles (Lower Third, Full Sentences)
    words = parse_srt(srt_path)
    if words:
        chunks = group_words_into_chunks(words, words_per_chunk=8) # 8 words per chunk for long form
        caption_y = int(VIDEO_HEIGHT * 0.85)
        font_size = 65 # Smaller font for long form
        subtitle_clips = create_subtitle_clips(chunks, y_pos=caption_y, font_size=font_size, content_type=content_type)
        final_video = CompositeVideoClip([bg_clip] + subtitle_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
    else:
        final_video = bg_clip
        
    print("  💾 Writing final long-form video...")
    final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None)
    
    # Close resources
    audio.close()
    final_video.close()
    return output_path
