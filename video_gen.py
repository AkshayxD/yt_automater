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
from moviepy.audio.AudioClip import CompositeAudioClip
import numpy as np

# --- Configuration ---
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
SUBTITLE_MAX_WIDTH = 1000

# --- Font ---
# Montserrat ExtraBold — the #1 viral Shorts font (used by Hormozi, MrBeast, etc.)
# Falls back to Impact if font file not found
FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "fonts", "Montserrat-ExtraBold.ttf"))
if os.environ.get("GITHUB_ACTIONS") == "true":
    FONT_NAME = "Montserrat-ExtraBold"
elif os.path.exists(FONT_PATH):
    FONT_NAME = FONT_PATH
else:
    # Fallback for systems where the font isn't downloaded yet
    FONT_NAME = "Impact" if os.name == 'nt' else "Arial-Bold"
    print(f"  Note: Montserrat-ExtraBold.ttf not found, using {FONT_NAME}")

# --- Subtitle Styling ---
# Yellow text + thick black stroke = #1 viral Reddit/narration Shorts style
# Used by SpeedyMorph, WrathOfGod, top Reddit narration & true crime channels
# The yellow pops on ANY background color (dark or bright gameplay footage)
#
# NOTE: Using RGB tuple instead of hex — some ImageMagick versions parse
# hex colors incorrectly, causing white/invisible text.
ACTIVE_COLOR = 'yellow'  # Bright viral yellow — pops on any BG
INACTIVE_COLOR = 'yellow'
ACTIVE_FONT_SIZE = 95              # Base size (±3px random per video for fingerprint variation)
STROKE_WIDTH = 12                  # Thick black stroke for maximum contrast (MrBeast/Reddit style)
STROKE_COLOR = 'black'

# 1 word per chunk for viral TikTok/Shorts "karaoke" style
WORDS_PER_CHUNK = 1

# --- Inspiration Style Overrides ---
# White text with thinner stroke, smaller font — clean, premium, philosophical aesthetic
INSP_ACTIVE_COLOR = 'white'
INSP_FONT_SIZE = 80
INSP_STROKE_WIDTH = 8
INSP_POP_SCALE = 1.15       # Subtler pop animation (vs 1.25 for story)
INSP_ZOOM_MIN = 1.01        # Slower zoom drift (calmer feel)
INSP_ZOOM_MAX = 1.04
INSP_MUSIC_VOLUME = 0.15    # Slightly louder atmospheric music
INSP_BG_DIR = os.path.join('assets', 'inspiration_bg')
INSP_MUSIC_DIR = os.path.join('assets', 'inspiration_music')


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


def create_subtitle_clips(chunks, y_pos=None, font_size=None, content_type="story"):
    """
    Creates single-line centered subtitle clips with the viral Shorts style.

    Args:
        chunks: List of word chunks with timing.
        y_pos: Vertical position in pixels. If None, uses 55% of frame height.
        font_size: Override font size. If None, uses ACTIVE_FONT_SIZE.
        content_type: 'story' or 'inspiration' — changes text color and style.

    Returns a list of moviepy clips (text + background bars interleaved).
    """
    subtitle_clips = []
    if y_pos is None:
        y_pos = int(VIDEO_HEIGHT * 0.55)
    
    # Select style based on content type
    if content_type == "inspiration":
        text_color = INSP_ACTIVE_COLOR
        stroke_w = INSP_STROKE_WIDTH
        pop_scale = INSP_POP_SCALE
        if font_size is None:
            font_size = INSP_FONT_SIZE
    else:
        text_color = ACTIVE_COLOR
        stroke_w = STROKE_WIDTH
        pop_scale = 1.25
        if font_size is None:
            font_size = ACTIVE_FONT_SIZE

    for chunk in chunks:
        display_text = chunk['text'].upper()
        start = chunk['start']
        end = chunk['end']

        # --- Stroke layer (rendered behind main text) ---
        stroke_clip = TextClip(
            display_text,
            fontsize=font_size,
            color='black',            # The core is black
            font=FONT_NAME,
            stroke_color='black',     # The stroke is black
            stroke_width=stroke_w,
            method='label',          
            align='center'
        )

        # --- Text layer (main fill, NO stroke) ---
        # Add a very thin 2px black stroke as an anti-aliasing buffer.
        # This completely absorbs any jagged edges/fringes on Linux transparent backgrounds
        # without shrinking the inner fill readability.
        txt_clip = TextClip(
            display_text,
            fontsize=font_size,
            color=text_color,         # Yellow for story, white for inspiration
            font=FONT_NAME,
            stroke_color='black',
            stroke_width=2,
            method='label',           
            align='center'
        )

        # Clamp width — if text is wider than max, fall back to caption method
        if stroke_clip.w > SUBTITLE_MAX_WIDTH:
            stroke_clip.close()
            txt_clip.close()
            
            stroke_clip = TextClip(
                display_text,
                fontsize=font_size,
                color='black',
                font=FONT_NAME,
                stroke_color='black',
                stroke_width=stroke_w,
                method='caption',
                size=(SUBTITLE_MAX_WIDTH, None),
                align='center'
            )
            txt_clip = TextClip(
                display_text,
                fontsize=font_size,
                color=text_color,
                font=FONT_NAME,
                stroke_color='black',
                stroke_width=2,
                method='caption',
                size=(SUBTITLE_MAX_WIDTH, None),
                align='center'
            )

        # --- Dark background bar behind text ---
        bar_padding_x = 28
        bar_padding_y = 14
        bar_w = min(stroke_clip.w + bar_padding_x * 2, VIDEO_WIDTH)
        bar_h = stroke_clip.h + bar_padding_y * 2

        bg_bar = (ColorClip(size=(bar_w, bar_h), color=(0, 0, 0))
                  .set_opacity(0.55)
                  .set_start(start)
                  .set_end(end)
                  .set_position(('center', y_pos - bar_padding_y)))

        # --- Viral Pop Animation ---
        # Capture pop_scale in a local variable for the closure
        _pop_scale = pop_scale
        _pop_rate = (_pop_scale - 1.0) / 0.07  # Rate to reach 1.0 from pop_scale in 0.07s
        def pop_effect(t, _s=_pop_scale, _r=_pop_rate):
            if t < 0.07:
                return _s - (_r * t)  
            return 1.0

        stroke_clip = (stroke_clip
                       .set_position(('center', y_pos))
                       .set_start(start)
                       .set_end(end)
                       .resize(pop_effect))

        txt_clip = (txt_clip
                    .set_position(('center', y_pos))
                    .set_start(start)
                    .set_end(end)
                    .resize(pop_effect))

        # Layer order: bar (back) → stroke → text (front)
        subtitle_clips.append(bg_bar)
        subtitle_clips.append(stroke_clip)
        subtitle_clips.append(txt_clip)

    return subtitle_clips


def trim_audio_silence(audio_clip, threshold_db=-40):
    """
    Trims trailing silence from the audio to create an abrupt ending.
    This forces rewatches and boosts completion rate.
    Falls back gracefully if audio analysis fails.
    
    Tighter 0.05s buffer (was 0.15s) — the more abrupt the ending,
    the more likely a rewatch ("wait, what did they say?").
    """
    try:
        fps = audio_clip.fps or 44100
        
        # Fix the MoviePy + NumPy TypeError compatibility bug:
        # Instead of calling self.to_soundarray() which fails by passing a generator
        # to np.vstack, we manually collect the chunks in a list (sequence type) and stack.
        buffersize = int(fps * 0.1)  # 100ms chunks
        chunks = []
        for chunk in audio_clip.iter_chunks(fps=fps, chunksize=buffersize, quantize=True, nbytes=2):
            chunks.append(chunk)
            
        if not chunks:
            return audio_clip
            
        audio_array = np.vstack(chunks) if audio_clip.nchannels > 1 else np.hstack(chunks)

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
            # 0.05s buffer — ultra-tight cut for maximum abruptness
            end_sample = last_sound + int(fps * 0.05)
            end_time = min(end_sample / fps, audio_clip.duration)
            time_saved = audio_clip.duration - end_time
            if time_saved > 0.2:
                print(f"  ✂️ Trimmed {time_saved:.1f}s of trailing silence (abrupt ending)")
                return audio_clip.subclip(0, end_time)
    except Exception as e:
        print(f"  Note: Skipping silence trim ({type(e).__name__})")

    return audio_clip


def create_video(audio_path, srt_path, background_path="assets/background_small.mp4",
                 output_path="final_video.mp4", bg_start_time=None, content_type="story"):
    """
    Assembles the final video by combining background, audio, and animated captions.

    Args:
        audio_path: Path to the voiceover MP3.
        srt_path: Path to the word-level SRT subtitle file.
        background_path: Path to the background video file.
        output_path: Where to save the final MP4.
        bg_start_time: If provided, use this exact start time in the background video.
                       If None, picks a random start (legacy behavior).
                       Set by background_manager.pick_background_segment() to ensure
                       no two shorts use the same footage from the same file.
        content_type: 'story' or 'inspiration' — selects visual style, music source,
                      and subtitle colors.

    Features:
    - Word-level synced subtitles (exact timing from edge-tts WordBoundary)
    - Montserrat ExtraBold font — viral Shorts standard
    - 3 words per chunk, single centered line — no overlap
    - Dark gradient overlay for text readability
    - Abrupt ending (trailing silence trimmed)
    - Optimized for 1080x1920 vertical (YouTube Shorts)
    - Dual style: yellow text + fast zoom (story) vs white text + slow zoom (inspiration)
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
    # All backgrounds are CC0 (Pixabay License or equivalent) — safe for monetization.
    # The bg_start_time is managed by background_manager to avoid reusing footage.
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

        # Use the manager-assigned start time if provided, else pick randomly
        if bg_start_time is not None:
            start_time = bg_start_time
        else:
            max_start = max(0, bg_clip.duration - audio_duration)
            start_time = random.uniform(0, max_start)

        end_time = min(start_time + audio_duration, bg_clip.duration)
        bg_clip = bg_clip.subclip(start_time, end_time)

        # Crop to vertical 9:16
        # Random ±50px horizontal offset = every video has a unique pixel fingerprint
        # Prevents YouTube's visual deduplication from flagging the channel as automated
        bg_clip = bg_clip.resize(height=VIDEO_HEIGHT)
        w, h = bg_clip.size
        x_center = w / 2
        half_width = VIDEO_WIDTH / 2
        crop_offset = random.randint(-50, 50)  # Unique per video
        x1 = max(0, x_center - half_width + crop_offset)
        x2 = min(w, x_center + half_width + crop_offset)
        bg_clip = bg_clip.crop(x1=x1, y1=0, x2=x2, y2=VIDEO_HEIGHT)

        # --- Subtle Zoom Drift ---
        # Background slowly zooms 1.0x → 1.05x over the video duration.
        # Keeps eyes engaged — static backgrounds feel dead and boring.
        # Inspiration uses a slower, calmer zoom.
        if content_type == "inspiration":
            zoom_target = random.uniform(INSP_ZOOM_MIN, INSP_ZOOM_MAX)
        else:
            zoom_target = random.uniform(1.03, 1.07)
        def zoom_drift(t):
            progress = t / max(audio_duration, 0.1)
            return 1.0 + (zoom_target - 1.0) * progress
        bg_clip = bg_clip.resize(zoom_drift)
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

    # --- Background Music (CC0 tracks) ---
    # Select music directory and volume based on content type
    if content_type == "inspiration":
        music_dir = INSP_MUSIC_DIR
        music_vol = INSP_MUSIC_VOLUME
    else:
        music_dir = os.path.join('assets', 'music')
        music_vol = 0.12
    
    music_files = glob.glob(os.path.join(music_dir, '*.mp3'))
    # Fallback: if inspiration music dir is empty, try the regular music dir
    if not music_files and content_type == "inspiration":
        music_files = glob.glob(os.path.join('assets', 'music', '*.mp3'))
    
    if music_files:
        music_path = random.choice(music_files)
        music_name = os.path.basename(music_path)
        print(f"  Adding background music: {music_name} (vol={music_vol})")
        try:
            music = AudioFileClip(music_path)
            # Loop music if shorter than the video
            if music.duration < audio_duration:
                from moviepy.audio.fx.all import audio_loop
                music = music.fx(audio_loop, duration=audio_duration)
            else:
                music = music.subclip(0, audio_duration)
            music = music.volumex(music_vol)
            mixed_audio = CompositeAudioClip([audio, music])
        except Exception as e:
            print(f"  Note: Music load failed ({e}) — using voiceover only")
            mixed_audio = audio
    else:
        print(f"  No music files in {music_dir}/ — add CC0 .mp3 files for better retention")
        mixed_audio = audio

    # Attach mixed audio
    video_with_audio = bg_clip.set_audio(mixed_audio)

    # --- Random caption y-position ---
    # Inspiration: centered at 50%, Story: random 45%-60%
    if content_type == "inspiration":
        caption_y = int(VIDEO_HEIGHT * 0.50)
    else:
        caption_y = int(VIDEO_HEIGHT * random.uniform(0.45, 0.60))

    # --- Random font size (±3px) for anti-fingerprinting ---
    base_size = INSP_FONT_SIZE if content_type == "inspiration" else ACTIVE_FONT_SIZE
    vid_font_size = base_size + random.randint(-3, 3)

    # --- Animated Subtitles ---
    print("  Generating animated subtitles...")
    words = parse_srt(srt_path)

    if not words:
        print("  ⚠️ No subtitles found in SRT file!")
        subtitle_clips = []
    else:
        chunks = group_words_into_chunks(words)
        subtitle_clips = create_subtitle_clips(chunks, y_pos=caption_y, font_size=vid_font_size, content_type=content_type)
        print(f"  Created {len(subtitle_clips)} subtitle clips "
              f"from {len(words)} words ({WORDS_PER_CHUNK} words/chunk) "
              f"at y={caption_y}px, font={vid_font_size}px, style={content_type}")

    # --- Composite Everything ---
    print("  Compositing layers...")
    all_clips = [video_with_audio, gradient_top, gradient_bottom] + subtitle_clips
    final_video = CompositeVideoClip(all_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    # --- Seamless Loop Ending ---
    # Cross-fade the last 0.5s into the first frame → viewers unknowingly
    # rewatch → 100%+ retention → massive algorithm boost
    try:
        loop_duration = 0.4
        if final_video.duration > loop_duration * 3:
            # Get the first frame as a static clip
            first_frame = final_video.to_ImageClip(t=0).set_duration(loop_duration)
            first_frame = first_frame.set_start(final_video.duration - loop_duration)
            first_frame = first_frame.crossfadein(loop_duration)
            final_video = CompositeVideoClip(
                [final_video, first_frame],
                size=(VIDEO_WIDTH, VIDEO_HEIGHT)
            )
            print(f"  🔄 Seamless loop ending applied ({loop_duration}s crossfade)")
    except Exception as e:
        print(f"  Note: Loop ending skipped ({type(e).__name__})")

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
