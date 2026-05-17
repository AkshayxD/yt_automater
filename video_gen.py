import os
import sys
import glob
import random
import re

# Fix Windows console encoding for emoji in log output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Auto-detect ImageMagick on Windows (moviepy needs this)
if os.name == 'nt' and not os.environ.get('IMAGEMAGICK_BINARY'):
    magick_paths = glob.glob(r'C:\Program Files\ImageMagick*\magick.exe')
    if magick_paths:
        os.environ['IMAGEMAGICK_BINARY'] = magick_paths[0]

from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    ColorClip, ImageClip
)
import numpy as np

# --- Configuration ---
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
SUBTITLE_MAX_WIDTH = 950

# Subtitle styling
FONT_NAME = "Impact" if os.name == 'nt' else "Arial-Bold"
ACTIVE_COLOR = '#FFD700'          # Gold/yellow for the active word chunk
INACTIVE_COLOR = 'white'          # White for context words
ACTIVE_FONT_SIZE = 100
INACTIVE_FONT_SIZE = 80
STROKE_WIDTH = 5

# How many words per subtitle chunk for the "karaoke" effect
WORDS_PER_CHUNK = 3


def parse_vtt(vtt_file):
    """
    Parses a VTT file and returns a list of subtitle cues.
    Each cue has 'start', 'end' (in seconds), and 'text'.
    """
    with open(vtt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match timestamps and text in VTT
    pattern = re.compile(
        r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})\n(.*?)(?=\n\n|\Z)',
        re.DOTALL
    )
    matches = pattern.findall(content)

    subs = []
    for match in matches:
        start_str, end_str, text = match

        def time_to_sec(t):
            t = t.replace(',', '.')
            h, m, s = t.split(':')
            sec, ms = s.split('.')
            return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000.0

        start_sec = time_to_sec(start_str)
        end_sec = time_to_sec(end_str)

        cleaned = text.strip()
        if cleaned:
            subs.append({
                'start': start_sec,
                'end': end_sec,
                'text': cleaned
            })

    return subs


def split_subs_into_word_chunks(subs, words_per_chunk=WORDS_PER_CHUNK):
    """
    Takes sentence-level subtitles from edge-tts and splits them into
    word-level chunks with estimated timing.
    
    Since edge-tts gives us sentence timing, we distribute the duration
    proportionally across words (by character length as a rough proxy
    for spoken duration).
    
    Returns a list of chunks, each with:
      - 'text': the chunk text (2-3 words)
      - 'start': estimated start time
      - 'end': estimated end time
    """
    all_chunks = []

    for sub in subs:
        words = sub['text'].split()
        if not words:
            continue

        duration = sub['end'] - sub['start']

        # Calculate character-weighted timing
        # Longer words take more time to say
        char_counts = [max(len(w), 1) for w in words]
        total_chars = sum(char_counts)

        # Build word-level timing
        word_entries = []
        current_time = sub['start']
        for i, word in enumerate(words):
            word_duration = (char_counts[i] / total_chars) * duration
            word_entries.append({
                'text': word,
                'start': current_time,
                'end': current_time + word_duration
            })
            current_time += word_duration

        # Group words into chunks of WORDS_PER_CHUNK
        for i in range(0, len(word_entries), words_per_chunk):
            group = word_entries[i:i + words_per_chunk]
            chunk = {
                'text': ' '.join(w['text'] for w in group),
                'start': group[0]['start'],
                'end': group[-1]['end']
            }
            all_chunks.append(chunk)

    return all_chunks


def create_gradient_overlay(width, height):
    """
    Creates a dark gradient overlay (top and bottom edges) that makes
    text pop against any background footage. This is the "premium" look.
    Returns a numpy RGB array.
    """
    # Create a dark gradient image
    overlay = np.zeros((height, width, 3), dtype=np.uint8)

    # Top gradient: dark to transparent (first 20% of height)
    top_h = height // 5
    for y in range(top_h):
        brightness = int(255 * (y / top_h))  # Goes from 0 (black) to 255 (transparent)
        # We set pixels to black; opacity will be controlled by the clip
        pass  # We'll handle this differently

    # Bottom gradient: transparent to dark (last 25% of height)
    bot_h = height // 4
    for y in range(bot_h):
        actual_y = height - bot_h + y
        # Goes from transparent to black
        pass

    return overlay


def create_subtitle_clips(chunks, audio_duration):
    """
    Creates animated subtitle clips with the "karaoke highlight" effect:
    
    - Chunks are grouped into "screens" (pairs of chunks displayed together)
    - The currently-spoken chunk is highlighted in GOLD with a larger font
    - Other visible chunks are shown in WHITE with a smaller font
    - Position: slightly above center to avoid YouTube's UI overlay
    
    Returns a list of moviepy TextClips.
    """
    subtitle_clips = []

    # Group chunks into "screens" — each screen shows 2 chunks stacked vertically
    # This gives context (you see what's coming next) while highlighting what's active
    screens = []
    for i in range(0, len(chunks), 2):
        screen_chunks = chunks[i:i + 2]
        screens.append(screen_chunks)

    for screen in screens:
        # For each chunk in this screen, create a time window where IT is highlighted
        for active_idx in range(len(screen)):
            active_chunk = screen[active_idx]

            for chunk_idx, chunk in enumerate(screen):
                is_active = (chunk_idx == active_idx)

                # Create the text clip
                display_text = chunk['text'].upper()

                txt_clip = TextClip(
                    display_text,
                    fontsize=ACTIVE_FONT_SIZE if is_active else INACTIVE_FONT_SIZE,
                    color=ACTIVE_COLOR if is_active else INACTIVE_COLOR,
                    font=FONT_NAME,
                    stroke_color='black',
                    stroke_width=STROKE_WIDTH if is_active else 3,
                    method='caption',
                    size=(SUBTITLE_MAX_WIDTH, None)
                )

                # Vertical positioning — slightly above center
                # YouTube's like/comment/share buttons are at bottom-right
                base_y = VIDEO_HEIGHT * 0.40  # 40% from top

                # Stack chunks vertically within the screen
                y_offset = int(base_y + (chunk_idx * 120))

                txt_clip = (txt_clip
                            .set_position(('center', y_offset))
                            .set_start(active_chunk['start'])
                            .set_end(active_chunk['end']))

                subtitle_clips.append(txt_clip)

    return subtitle_clips


def trim_audio_silence(audio_clip, threshold_db=-40):
    """
    Trims trailing silence from the audio to create an abrupt ending.
    This forces rewatches and boosts completion rate.
    Falls back gracefully if audio analysis fails.
    """
    try:
        fps = audio_clip.fps or 44100
        # to_soundarray can fail with some moviepy/ffmpeg versions
        audio_array = audio_clip.to_soundarray(fps=fps)

        if audio_array is None or len(audio_array) == 0:
            return audio_clip

        if len(audio_array.shape) > 1:
            amplitudes = np.max(np.abs(audio_array), axis=1)
        else:
            amplitudes = np.abs(audio_array)

        # Convert threshold from dB to linear
        threshold = 10 ** (threshold_db / 20.0)

        # Find last sample above threshold
        non_silent = np.where(amplitudes > threshold)[0]

        if len(non_silent) > 0:
            last_sound = non_silent[-1]
            # Add tiny buffer (0.15s) then cut — abrupt but not jarring
            end_sample = last_sound + int(fps * 0.15)
            end_time = min(end_sample / fps, audio_clip.duration)
            time_saved = audio_clip.duration - end_time
            if time_saved > 0.3:
                print(f"  Trimmed {time_saved:.1f}s of trailing silence")
                return audio_clip.subclip(0, end_time)
    except Exception as e:
        print(f"  Note: Skipping silence trim ({type(e).__name__})")

    return audio_clip


def create_video(audio_path, vtt_path, background_path="assets/background_small.mp4",
                 output_path="final_video.mp4"):
    """
    Assembles the final video by combining background, audio, and animated captions.
    
    Features:
    - Word-by-word animated subtitles with gold highlight on active words
    - Dark gradient overlay for premium text readability
    - Abrupt ending (no trailing silence) for higher completion rate
    - Optimized for 1080x1920 vertical format (YouTube Shorts)
    - Random background segment selection for variety
    """
    print("  Assembling final video...")

    # Load audio and trim trailing silence for abrupt ending
    audio = AudioFileClip(audio_path)
    audio = trim_audio_silence(audio)
    audio_duration = audio.duration
    print(f"  Audio duration: {audio_duration:.1f}s")

    if audio_duration > 59.5:
        print("  ⚠️ Audio exceeds 59.5s — trimming to fit Shorts limit")
        audio = audio.subclip(0, 59.5)
        audio_duration = 59.5

    # --- Background Video ---
    bg_clip = None

    if not os.path.exists(background_path):
        # Try to find ANY video in the assets folder
        assets_dir = os.path.dirname(background_path) or "assets"
        if os.path.exists(assets_dir):
            bg_files = [f for f in os.listdir(assets_dir)
                        if f.lower().endswith(('.mp4', '.webm', '.mov'))]
            if bg_files:
                background_path = os.path.join(assets_dir, random.choice(bg_files))
                print(f"  Using alternate background: {os.path.basename(background_path)}")

    if os.path.exists(background_path):
        bg_clip = VideoFileClip(background_path)

        # Make sure background is longer than audio
        if bg_clip.duration < audio_duration:
            print("  Background shorter than audio — looping...")
            from moviepy.video.fx.all import loop
            bg_clip = bg_clip.fx(loop, duration=audio_duration)

        # Pick a random starting point for variety
        max_start = max(0, bg_clip.duration - audio_duration)
        start_time = random.uniform(0, max_start)
        bg_clip = bg_clip.subclip(start_time, start_time + audio_duration)

        # Crop to vertical 9:16
        bg_clip = bg_clip.resize(height=VIDEO_HEIGHT)
        w, h = bg_clip.size
        x_center = w / 2
        half_width = VIDEO_WIDTH / 2
        bg_clip = bg_clip.crop(
            x1=x_center - half_width, y1=0,
            x2=x_center + half_width, y2=VIDEO_HEIGHT
        )
    else:
        print("  ⚠️ No background video found — using dark background")
        bg_clip = ColorClip(
            size=(VIDEO_WIDTH, VIDEO_HEIGHT),
            color=(12, 12, 20),  # Near-black with subtle blue tint
            duration=audio_duration
        )

    # --- Dark Gradient Overlay ---
    # Semi-transparent black at top and bottom edges for text readability
    gradient_top = (ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT // 4), color=(0, 0, 0))
                    .set_duration(audio_duration)
                    .set_position(('center', 'top'))
                    .set_opacity(0.3))

    gradient_bottom = (ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT // 3), color=(0, 0, 0))
                       .set_duration(audio_duration)
                       .set_position(('center', 'bottom'))
                       .set_opacity(0.4))

    # Attach the audio
    video_with_audio = bg_clip.set_audio(audio)

    # --- Animated Subtitles ---
    print("  Generating animated subtitles...")
    subs = parse_vtt(vtt_path)

    if not subs:
        print("  ⚠️ No subtitles found in VTT file!")
        subtitle_clips = []
    else:
        # Split sentence-level subs into word-level chunks
        chunks = split_subs_into_word_chunks(subs)
        subtitle_clips = create_subtitle_clips(chunks, audio_duration)
        print(f"  Created {len(subtitle_clips)} subtitle clips "
              f"from {len(chunks)} word chunks")

    # --- Composite Everything ---
    print("  Compositing layers...")
    all_clips = [video_with_audio, gradient_top, gradient_bottom] + subtitle_clips
    final_video = CompositeVideoClip(all_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    # --- Render ---
    print("  Rendering final MP4 (this may take a while)...")
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset='medium',     # Good quality/speed balance
        bitrate='8000k',     # High bitrate for crisp Shorts
        logger=None          # Suppress massive progress bars
    )

    # Clean up
    audio.close()
    if isinstance(bg_clip, VideoFileClip):
        bg_clip.close()
    final_video.close()

    print(f"  ✅ Video rendered: {output_path}")
    return output_path


if __name__ == "__main__":
    if os.path.exists("temp/audio.mp3") and os.path.exists("temp/subs.vtt"):
        create_video("temp/audio.mp3", "temp/subs.vtt", output_path="temp/test_output.mp4")
    else:
        print("No test audio/subs found. Run audio_gen.py first.")
