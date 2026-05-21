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
    ColorClip
)
import numpy as np

# --- Configuration ---
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
SUBTITLE_MAX_WIDTH = 1000

# --- Font ---
# Montserrat ExtraBold — the #1 viral Shorts font (used by Hormozi, MrBeast, etc.)
# Falls back to Impact if font file not found
FONT_PATH = os.path.join("assets", "fonts", "Montserrat-ExtraBold.ttf")
if os.path.exists(FONT_PATH):
    FONT_NAME = FONT_PATH
else:
    # Fallback for systems where the font isn't downloaded yet
    FONT_NAME = "Impact" if os.name == 'nt' else "Arial-Bold"
    print(f"  Note: Montserrat-ExtraBold.ttf not found, using {FONT_NAME}")

# --- Subtitle Styling ---
ACTIVE_COLOR = 'yellow'            # Bright yellow for the active word chunk
INACTIVE_COLOR = 'white'           # White for context words (unused in single-line mode)
ACTIVE_FONT_SIZE = 88              # Montserrat is wider than Impact, so slightly smaller
STROKE_WIDTH = 4                   # Black outline for readability
STROKE_COLOR = 'black'

# How many words per subtitle chunk — 2 prevents overlap and syncs tighter
WORDS_PER_CHUNK = 2


def parse_srt(srt_file):
    """
    Parses an SRT file with word-level timing (from edge-tts WordBoundary).
    Each entry is a single word with its exact start/end time.

    Returns a list of dicts: [{'start': float, 'end': float, 'text': str}, ...]
    """
    with open(srt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # SRT format: index, timestamp line, text, blank line
    pattern = re.compile(
        r'(\d+)\n(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})\n(.*?)(?=\n\n|\n\d+\n|\Z)',
        re.DOTALL
    )
    matches = pattern.findall(content)

    def time_to_sec(t):
        t = t.replace(',', '.')
        h, m, s = t.split(':')
        sec, ms = s.split('.')
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000.0

    words = []
    for match in matches:
        _idx, start_str, end_str, text = match
        cleaned = text.strip()
        if cleaned:
            words.append({
                'start': time_to_sec(start_str),
                'end': time_to_sec(end_str),
                'text': cleaned
            })

    return words


def group_words_into_chunks(words, words_per_chunk=WORDS_PER_CHUNK):
    """
    Groups word-level SRT entries into chunks of N words.
    Uses the EXACT timestamps from edge-tts WordBoundary events —
    no estimation or character-proportion math needed.

    Returns a list of chunks:
      [{'text': '2 words here', 'start': exact_start, 'end': exact_end}, ...]
    """
    chunks = []
    for i in range(0, len(words), words_per_chunk):
        group = words[i:i + words_per_chunk]
        chunk = {
            'text': ' '.join(w['text'] for w in group),
            'start': group[0]['start'],
            'end': group[-1]['end']
        }
        chunks.append(chunk)
    return chunks


def create_subtitle_clips(chunks):
    """
    Creates single-line centered subtitle clips with the viral Shorts style:

    - ONE line at a time (no stacking) — this is what actual viral Shorts do
    - Each chunk is 2 words, displayed in ALL CAPS
    - Bright yellow text with thick black outline
    - Positioned at ~40% from top (above YouTube's UI buttons)

    Returns a list of moviepy TextClips.
    """
    subtitle_clips = []

    for chunk in chunks:
        display_text = chunk['text'].upper()

        txt_clip = TextClip(
            display_text,
            fontsize=ACTIVE_FONT_SIZE,
            color=ACTIVE_COLOR,
            font=FONT_NAME,
            stroke_color=STROKE_COLOR,
            stroke_width=STROKE_WIDTH,
            method='caption',
            size=(SUBTITLE_MAX_WIDTH, None)
        )

        # Center horizontally, position at 40% from top
        y_pos = int(VIDEO_HEIGHT * 0.40)

        txt_clip = (txt_clip
                    .set_position(('center', y_pos))
                    .set_start(chunk['start'])
                    .set_end(chunk['end']))

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
        audio_array = audio_clip.to_soundarray(fps=fps)

        if audio_array is None or len(audio_array) == 0:
            return audio_clip

        if len(audio_array.shape) > 1:
            amplitudes = np.max(np.abs(audio_array), axis=1)
        else:
            amplitudes = np.abs(audio_array)

        threshold = 10 ** (threshold_db / 20.0)
        non_silent = np.where(amplitudes > threshold)[0]

        if len(non_silent) > 0:
            last_sound = non_silent[-1]
            end_sample = last_sound + int(fps * 0.15)
            end_time = min(end_sample / fps, audio_clip.duration)
            time_saved = audio_clip.duration - end_time
            if time_saved > 0.3:
                print(f"  Trimmed {time_saved:.1f}s of trailing silence")
                return audio_clip.subclip(0, end_time)
    except Exception as e:
        print(f"  Note: Skipping silence trim ({type(e).__name__})")

    return audio_clip


def create_video(audio_path, srt_path, background_path="assets/background_small.mp4",
                 output_path="final_video.mp4"):
    """
    Assembles the final video by combining background, audio, and animated captions.

    Features:
    - Word-level synced subtitles (exact timing from edge-tts WordBoundary)
    - Montserrat ExtraBold font — viral Shorts standard
    - 2 words per chunk, single centered line — no overlap
    - Dark gradient overlay for text readability
    - Abrupt ending (trailing silence trimmed)
    - Optimized for 1080x1920 vertical (YouTube Shorts)
    """
    print("  Assembling final video...")

    # Load audio and trim trailing silence
    audio = AudioFileClip(audio_path)
    audio = trim_audio_silence(audio)
    audio_duration = audio.duration
    print(f"  Audio duration: {audio_duration:.1f}s")

    if audio_duration > 59.5:
        print("  ⚠️ Audio exceeds 59.5s — trimming to fit Shorts limit")
        audio = audio.subclip(0, 59.5)
        audio_duration = 59.5

    # --- Background Video ---
    # ONLY use Minecraft parkour videos (copyright-safe for monetization)
    bg_clip = None

    if not os.path.exists(background_path):
        # Try background.mp4 or background_small.mp4
        assets_dir = os.path.dirname(background_path) or "assets"
        for fallback in ["background_small.mp4", "background.mp4"]:
            fallback_path = os.path.join(assets_dir, fallback)
            if os.path.exists(fallback_path):
                background_path = fallback_path
                break

    if os.path.exists(background_path):
        bg_clip = VideoFileClip(background_path)

        # Loop if background is shorter than audio
        if bg_clip.duration < audio_duration:
            print("  Background shorter than audio — looping...")
            from moviepy.video.fx.all import loop
            bg_clip = bg_clip.fx(loop, duration=audio_duration)

        # Random starting point for variety across videos
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
            color=(12, 12, 20),
            duration=audio_duration
        )

    # --- Dark Gradient Overlay ---
    gradient_top = (ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT // 4), color=(0, 0, 0))
                    .set_duration(audio_duration)
                    .set_position(('center', 'top'))
                    .set_opacity(0.3))

    gradient_bottom = (ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT // 3), color=(0, 0, 0))
                       .set_duration(audio_duration)
                       .set_position(('center', 'bottom'))
                       .set_opacity(0.4))

    # Attach audio
    video_with_audio = bg_clip.set_audio(audio)

    # --- Animated Subtitles ---
    print("  Generating animated subtitles...")
    words = parse_srt(srt_path)

    if not words:
        print("  ⚠️ No subtitles found in SRT file!")
        subtitle_clips = []
    else:
        chunks = group_words_into_chunks(words)
        subtitle_clips = create_subtitle_clips(chunks)
        print(f"  Created {len(subtitle_clips)} subtitle clips "
              f"from {len(words)} words ({WORDS_PER_CHUNK} words/chunk)")

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
        preset='medium',
        bitrate='8000k',
        logger=None
    )

    # Clean up
    audio.close()
    if isinstance(bg_clip, VideoFileClip):
        bg_clip.close()
    final_video.close()

    print(f"  ✅ Video rendered: {output_path}")
    return output_path


if __name__ == "__main__":
    if os.path.exists("temp/audio.mp3") and os.path.exists("temp/subs.srt"):
        create_video("temp/audio.mp3", "temp/subs.srt", output_path="temp/test_output.mp4")
    else:
        print("No test audio/subs found. Run audio_gen.py first.")
