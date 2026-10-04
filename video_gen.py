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
ACTIVE_COLOR = '#00FF88'  # Changed to green per user request
INACTIVE_COLOR = '#00FF88'
ACTIVE_FONT_SIZE = 95              # Base size (±3px random per video for fingerprint variation)
STROKE_WIDTH = 12                  # Thick black stroke for maximum contrast (MrBeast/Reddit style)
STROKE_COLOR = 'black'

# 2-3 words per chunk for modern viral pacing
WORDS_PER_CHUNK = 2

# --- Inspiration Style Overrides ---
# White text with thinner stroke, smaller font — clean, premium, philosophical aesthetic
INSP_ACTIVE_COLOR = '#00FF88'
INSP_FONT_SIZE = 80
INSP_STROKE_WIDTH = 8
INSP_POP_SCALE = 1.15       # Subtler pop animation (vs 1.25 for story)
INSP_ZOOM_MIN = 1.01        # Slower zoom drift (calmer feel)
INSP_ZOOM_MAX = 1.04
INSP_MUSIC_VOLUME = 0.15    # Slightly louder atmospheric music
INSP_BG_DIR = os.path.join('assets', 'inspiration_bg')
INSP_MUSIC_DIR = os.path.join('assets', 'inspiration_music')

# --- Would You Rather Style ---
# Vibrant green text with exaggerated pop — quiz/game show energy
WYR_ACTIVE_COLOR = '#00FF88'
WYR_FONT_SIZE = 90
WYR_STROKE_WIDTH = 10
WYR_POP_SCALE = 1.30              # Exaggerated pop — energetic
WYR_ZOOM_MIN = 1.04
WYR_ZOOM_MAX = 1.08
WYR_BG_DIR = os.path.join('assets', 'wyr_bg')

# --- Fake Text Style ---
# Uses chat bubble rendering instead of standard subtitles (handled separately)
# Standard subtitles still used for the narration track
FT_ACTIVE_COLOR = '#00FF88'       # Light gray narration text
FT_FONT_SIZE = 85
FT_STROKE_WIDTH = 10
FT_POP_SCALE = 1.20
FT_BUBBLE_ME_COLOR = (0, 122, 255)     # iMessage blue for "me"
FT_BUBBLE_THEM_COLOR = (58, 58, 60)    # Dark gray for "them"
FT_BUBBLE_TEXT_COLOR = 'white'
FT_BUBBLE_FONT_SIZE = 32               # Smaller — chat text
FT_BG_DIR = os.path.join('assets', 'fake_text_bg')

# --- Dark Psychology Style ---
# Red accent text — danger/warning feel, authoritative
DP_ACTIVE_COLOR = '#00FF88'
DP_FONT_SIZE = 85
DP_STROKE_WIDTH = 10
DP_POP_SCALE = 1.20
DP_ZOOM_MIN = 1.02

# --- Quiz Style ---
# Vibrant orange/magenta text for fun game show feel
QUIZ_ACTIVE_COLOR = '#00FF88'
QUIZ_FONT_SIZE = 90
QUIZ_STROKE_WIDTH = 10
QUIZ_POP_SCALE = 1.25
QUIZ_ZOOM_MIN = 1.03
QUIZ_ZOOM_MAX = 1.07
QUIZ_BG_DIR = os.path.join('assets', 'quiz_bg')
QUIZ_MUSIC_DIR = os.path.join('assets', 'quiz_music')
QUIZ_MUSIC_VOLUME = 0.15
DP_ZOOM_MAX = 1.05
DP_BG_DIR = os.path.join('assets', 'dark_psych_bg')

# --- True Crime Style ---
# Pale gray text — washed out, eerie, minimal animation for creepy stillness
TC_ACTIVE_COLOR = '#CCCCCC'
TC_FONT_SIZE = 80
TC_STROKE_WIDTH = 8
TC_POP_SCALE = 1.10               # Minimal pop — slow, creepy
TC_ZOOM_MIN = 1.00                # Almost no zoom — static dread
TC_ZOOM_MAX = 1.02
TC_BG_DIR = os.path.join('assets', 'true_crime_bg')
TC_MUSIC_DIR = os.path.join('assets', 'true_crime_music')


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
        content_type: 'story', 'inspiration', 'would_you_rather', 'fake_text',
                      'dark_psychology', or 'true_crime' — changes text color and style.

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
    elif content_type == "would_you_rather":
        text_color = WYR_ACTIVE_COLOR
        stroke_w = WYR_STROKE_WIDTH
        pop_scale = WYR_POP_SCALE
        if font_size is None:
            font_size = WYR_FONT_SIZE
    elif content_type == "fake_text":
        text_color = FT_ACTIVE_COLOR
        stroke_w = FT_STROKE_WIDTH
        pop_scale = FT_POP_SCALE
        if font_size is None:
            font_size = FT_FONT_SIZE
    elif content_type == "dark_psychology":
        text_color = DP_ACTIVE_COLOR
        stroke_w = DP_STROKE_WIDTH
        pop_scale = DP_POP_SCALE
        if font_size is None:
            font_size = DP_FONT_SIZE
    elif content_type == "true_crime":
        text_color = TC_ACTIVE_COLOR
        stroke_w = TC_STROKE_WIDTH
        pop_scale = TC_POP_SCALE
        if font_size is None:
            font_size = TC_FONT_SIZE
    elif content_type == "quiz":
        text_color = QUIZ_ACTIVE_COLOR
        stroke_w = QUIZ_STROKE_WIDTH
        pop_scale = QUIZ_POP_SCALE
        if font_size is None:
            font_size = QUIZ_FONT_SIZE
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


def create_chat_bubble_clips(messages, audio_duration):
    """
    Renders iMessage-style chat bubbles for the fake_text content type.
    Bubbles stack from top to bottom, appearing sequentially.
    """
    if not messages:
        return []
        
    clips = []
    # Simplified timing: divide duration equally among messages, 
    # but first message starts a bit later.
    num_msgs = len(messages)
    start_delay = 2.0
    time_per_msg = (audio_duration - start_delay) / max(1, num_msgs)
    
    y_offset = int(VIDEO_HEIGHT * 0.15)  # Start 15% down from top
    bubble_spacing = 25
    
    for i, msg in enumerate(messages):
        sender = msg.get("sender", "them").lower()
        text = msg.get("text", "").upper()
        
        start_time = start_delay + (i * time_per_msg)
        
        # Color & Position based on sender
        if sender == "me":
            bg_color = FT_BUBBLE_ME_COLOR
            align = "right"
            x_pos = VIDEO_WIDTH - 60  # Right padding
        else:
            bg_color = FT_BUBBLE_THEM_COLOR
            align = "left"
            x_pos = 60  # Left padding
            
        # Text
        txt_clip = TextClip(
            text,
            fontsize=FT_BUBBLE_FONT_SIZE,
            color=FT_BUBBLE_TEXT_COLOR,
            font=FONT_NAME,
            method='caption',
            align=align,
            size=(int(VIDEO_WIDTH * 0.7), None)  # Max width 70% of screen
        )
        
        # Bubble Background (add padding)
        padding_x = 40
        padding_y = 30
        w, h = txt_clip.size
        bg_w, bg_h = w + padding_x, h + padding_y
        
        # We use ColorClip for the bubble background
        bubble_bg = ColorClip(size=(bg_w, bg_h), color=bg_color).set_opacity(0.95)
        
        # Composite text over background
        bubble = CompositeVideoClip([
            bubble_bg, 
            txt_clip.set_position('center')
        ], size=(bg_w, bg_h))
        
        # Calculate final x position based on alignment
        if align == "right":
            final_x = x_pos - bg_w
        else:
            final_x = x_pos
            
        # Animate bubble appearance (slide up slightly)
        bubble = bubble.set_start(start_time).set_end(audio_duration)
        
        # We need a closure to capture the loop variables properly
        def make_pos(final_x, y_off, st):
            def pos(t):
                if t - st < 0:
                    return (final_x, y_off + 50)  # Hidden/off before start
                elif t - st < 0.2:
                    return (final_x, y_off + max(0, 50 * (1 - (t - st) * 5)))
                return (final_x, y_off)
            return pos
            
        bubble = bubble.set_position(make_pos(final_x, y_offset, start_time))
        
        clips.append(bubble)
        y_offset += bg_h + bubble_spacing
        
    return clips


# --- Hook Card Configuration ---
# Duration of the hook card displayed before the voiceover starts
HOOK_CARD_DURATION = 1.2  # seconds — long enough to read, short enough to not bore
HOOK_CARD_FONT_SIZE = 72  # Slightly smaller than captions so multi-line text fits
HOOK_CARD_MAX_WIDTH = 900  # Max width before wrapping
HOOK_CARD_BG_OPACITY = 0.75  # Dark overlay opacity
HOOK_CARD_Y_POS = 0.40  # Vertical center-ish position (fraction of screen height)


def create_hook_card(hook_text, duration=HOOK_CARD_DURATION, content_type="story"):
    """
    Creates a 1.2-second "hook card" — a full-screen text overlay shown BEFORE
    the voiceover starts. This gives the viewer a reason to stop scrolling.

    The hook card shows the headline in large bold text on a semi-transparent
    dark background. It uses a scale-up + fade-in animation for visual punch.

    Args:
        hook_text: The headline text to display (will be uppercased).
        duration: How long the hook card is visible (seconds).
        content_type: Visual style to match the content type.

    Returns:
        A list of moviepy clips (dark overlay + stroke text + fill text),
        all timed from t=0 to t=duration.
    """
    if not hook_text or not hook_text.strip():
        return [], 0.0

    display_text = hook_text.strip().upper()

    # Select text color based on content type
    color_map = {
        "inspiration": INSP_ACTIVE_COLOR,
        "would_you_rather": WYR_ACTIVE_COLOR,
        "fake_text": FT_ACTIVE_COLOR,
        "dark_psychology": DP_ACTIVE_COLOR,
        "true_crime": TC_ACTIVE_COLOR,
        "quiz": QUIZ_ACTIVE_COLOR,
    }
    text_color = color_map.get(content_type, ACTIVE_COLOR)

    # --- Dark overlay behind the hook text ---
    dark_bg = (ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0))
               .set_opacity(HOOK_CARD_BG_OPACITY)
               .set_duration(duration)
               .set_start(0))

    # --- Hook text (stroke + fill layers) ---
    try:
        stroke_clip = TextClip(
            display_text,
            fontsize=HOOK_CARD_FONT_SIZE,
            color='black',
            font=FONT_NAME,
            stroke_color='black',
            stroke_width=STROKE_WIDTH,
            method='caption',
            size=(HOOK_CARD_MAX_WIDTH, None),
            align='center'
        )
        txt_clip = TextClip(
            display_text,
            fontsize=HOOK_CARD_FONT_SIZE,
            color=text_color,
            font=FONT_NAME,
            stroke_color='black',
            stroke_width=2,
            method='caption',
            size=(HOOK_CARD_MAX_WIDTH, None),
            align='center'
        )
    except Exception as e:
        print(f"  ⚠️ Hook card text rendering failed: {e}")
        return [], 0.0

    y_pos = int(VIDEO_HEIGHT * HOOK_CARD_Y_POS)

    # --- Scale-up animation: starts at 0.85x and scales to 1.0x ---
    def hook_scale(t):
        if t < 0.15:
            # Quick scale-up from 0.85 to 1.0 in first 150ms
            progress = t / 0.15
            return 0.85 + (0.15 * progress)
        return 1.0

    # --- Fade-in: opacity ramps from 0 to 1 in first 200ms ---
    def hook_fade(t):
        if t < 0.2:
            return t / 0.2
        # Fade out in last 200ms
        if t > duration - 0.2:
            return max(0, (duration - t) / 0.2)
        return 1.0

    stroke_clip = (stroke_clip
                   .set_position(('center', y_pos))
                   .set_start(0)
                   .set_end(duration)
                   .resize(hook_scale)
                   .set_opacity(hook_fade))

    txt_clip = (txt_clip
                .set_position(('center', y_pos))
                .set_start(0)
                .set_end(duration)
                .resize(hook_scale)
                .set_opacity(hook_fade))

    print(f"  🪝 Hook card: \"{display_text}\" ({duration}s)")
    return [dark_bg, stroke_clip, txt_clip], duration


def add_sfx_hits(audio_clip, words_data):
    """
    Scans the SRT data for dramatic words and inserts a programmatic impact SFX.
    No external audio files needed — generates a low sine wave burst.
    """
    sfx_clips = [audio_clip]
    dramatic_words = ["DEAD", "GONE", "NEVER", "ALWAYS", "WRONG", "SUDDENLY", "STOP", "NO", "KILLED", "DIED"]
    
    fps = 44100
    duration = 0.5
    t = np.linspace(0, duration, int(fps * duration), endpoint=False)
    # Generate a low impact sound (frequency drops rapidly)
    freqs = np.linspace(150, 40, len(t))
    audio_array = 0.5 * np.sin(2 * np.pi * freqs * t)
    # Fade out
    fade = np.linspace(1, 0, len(t))
    audio_array = audio_array * fade
    
    # We must format it as stereo for CompositeAudioClip
    stereo_array = np.column_stack((audio_array, audio_array))
    from moviepy.audio.AudioClip import AudioArrayClip
    sfx_base = AudioArrayClip(stereo_array, fps=fps).volumex(0.15)
    
    hits_added = 0
    # Add a minimum gap between SFX so it doesn't get annoying
    last_hit_time = -5.0
    
    for chunk in words_data:
        text = chunk['text'].upper().strip(".,!?\"'")
        # Only check single words or split
        chunk_words = text.split()
        if any(w in dramatic_words for w in chunk_words):
            start = chunk['start']
            if start - last_hit_time > 3.0 and start + duration < audio_clip.duration:
                sfx = sfx_base.set_start(start)
                sfx_clips.append(sfx)
                hits_added += 1
                last_hit_time = start
                
    if hits_added > 0:
        print(f"  🔊 Added {hits_added} dramatic SFX hits based on transcript")
        return CompositeAudioClip(sfx_clips)
    return audio_clip


def create_video(audio_path, srt_path, background_path="assets/background_small.mp4",
                 output_path="final_video.mp4", bg_start_time=None, content_type="story", messages=None, popup_image_path=None, popup_trigger_word=None, hook_text=None, video_format="short"):
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
        content_type: 'story', 'inspiration', 'would_you_rather', 'fake_text',
                       'dark_psychology', or 'true_crime' — selects visual style,
                       music source, and subtitle colors.

    Features:
    - Word-level synced subtitles (exact timing from edge-tts WordBoundary)
    - Montserrat ExtraBold font — viral Shorts standard
    - 3 words per chunk, single centered line — no overlap
    - Dark gradient overlay for text readability
    - Abrupt ending (trailing silence trimmed)
    - Optimized for 1080x1920 vertical (YouTube Shorts)
    - 6 visual styles: story/inspiration/wyr/fake_text/dark_psych/true_crime
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

        # Crop/Rotate background based on video format
        if video_format == "long":
            v_width = 1920
            v_height = 1080
            # Resize so width fills 1920, then crop top/bottom
            bg_clip = bg_clip.resize(width=v_width)
            w, h = bg_clip.size
            if h > v_height:
                y_center = h / 2
                half_height = v_height / 2
                bg_clip = bg_clip.crop(x1=0, y1=y_center-half_height, x2=v_width, y2=y_center+half_height)
            else:
                bg_clip = bg_clip.resize(height=v_height, width=v_width)
        else:
            v_width = VIDEO_WIDTH
            v_height = VIDEO_HEIGHT
            bg_clip = bg_clip.resize(height=v_height)
            w, h = bg_clip.size
            x_center = w / 2
            half_width = v_width / 2
            crop_offset = random.randint(-50, 50)
            x1 = max(0, x_center - half_width + crop_offset)
            x2 = min(w, x_center + half_width + crop_offset)
            bg_clip = bg_clip.crop(x1=x1, y1=0, x2=x2, y2=v_height)

        # --- Subtle Zoom Drift ---
        # Background slowly zooms 1.0x → 1.05x over the video duration.
        # Keeps eyes engaged — static backgrounds feel dead and boring.
        # Each content type uses its own zoom range for the right feel.
        zoom_ranges = {
            "inspiration": (INSP_ZOOM_MIN, INSP_ZOOM_MAX),
            "would_you_rather": (WYR_ZOOM_MIN, WYR_ZOOM_MAX),
            "dark_psychology": (DP_ZOOM_MIN, DP_ZOOM_MAX),
            "true_crime": (TC_ZOOM_MIN, TC_ZOOM_MAX),
            "quiz": (QUIZ_ZOOM_MIN, QUIZ_ZOOM_MAX),
        }
        z_min, z_max = zoom_ranges.get(content_type, (1.03, 1.07))
        zoom_target = random.uniform(z_min, z_max)
        def zoom_drift(t):
            progress = t / max(audio_duration, 0.1)
            return 1.0 + (zoom_target - 1.0) * progress
        bg_clip = bg_clip.resize(zoom_drift)
    else:
        print("  ⚠️ No background video found — using dark background")
        bg_clip = ColorClip(
            size=(1920 if video_format == "long" else VIDEO_WIDTH, 1080 if video_format == "long" else VIDEO_HEIGHT),
            color=(12, 12, 20),
            duration=audio_duration
        )

    # --- Dark Gradient Overlay ---
    # Removed per user request
    # gradient_top = (ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT // 4), color=(0, 0, 0))
    #                 .set_duration(audio_duration)
    #                 .set_position(('center', 'top'))
    #                 .set_opacity(0.3))

    # gradient_bottom = (ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT // 3), color=(0, 0, 0))
    #                    .set_duration(audio_duration)
    #                    .set_position(('center', 'bottom'))
    #                    .set_opacity(0.4))

    # --- Background Music (CC0 tracks) ---
    # Select music directory and volume based on content type
    music_config = {
        "inspiration": (INSP_MUSIC_DIR, INSP_MUSIC_VOLUME),
        "true_crime": (TC_MUSIC_DIR, 0.18),          # Louder eerie ambient
        "dark_psychology": (os.path.join('assets', 'music'), 0.10),  # Subtle
        "would_you_rather": (os.path.join('assets', 'music'), 0.08), # Very subtle
        "fake_text": (os.path.join('assets', 'music'), 0.08),        # Very subtle
        "quiz": (QUIZ_MUSIC_DIR, QUIZ_MUSIC_VOLUME),
    }
    music_dir, music_vol = music_config.get(content_type, (os.path.join('assets', 'music'), 0.12))
    
    music_files = glob.glob(os.path.join(music_dir, '*.mp3'))
    # Fallback: if type-specific music dir is empty, try the regular music dir
    if not music_files and content_type != "story":
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

    words = parse_srt(srt_path)

    # --- Auto SFX Hits ---
    if content_type in ["true_crime", "dark_psychology", "story", "would_you_rather"]:
        if words:
            mixed_audio = add_sfx_hits(mixed_audio, words)

    # Attach mixed audio
    video_with_audio = bg_clip.set_audio(mixed_audio)

    # --- Random caption y-position ---
    # Each content type has its preferred caption position
    caption_y_map = {
        "inspiration": 0.50,
        "dark_psychology": 0.52,
        "true_crime": 0.50,
        "quiz": 0.50,
    }
    if video_format == "long":
        caption_y = int(1080 * 0.85)  # Lower third
    else:
        if content_type in caption_y_map:
            caption_y = int(VIDEO_HEIGHT * caption_y_map[content_type])
        else:
            caption_y = int(VIDEO_HEIGHT * random.uniform(0.45, 0.60))

    # --- Random font size (±3px) for anti-fingerprinting ---
    font_size_map = {
        "inspiration": INSP_FONT_SIZE,
        "would_you_rather": WYR_FONT_SIZE,
        "fake_text": FT_FONT_SIZE,
        "dark_psychology": DP_FONT_SIZE,
        "true_crime": TC_FONT_SIZE,
        "quiz": QUIZ_FONT_SIZE,
    }
    base_size = font_size_map.get(content_type, ACTIVE_FONT_SIZE)
    vid_font_size = base_size + random.randint(-3, 3)

    # --- Animated Subtitles ---
    print("  Generating animated subtitles...")

    if not words:
        print("  ⚠️ No subtitles found in SRT file!")
        subtitle_clips = []
    else:
        words_per_chunk = 8 if video_format == "long" else WORDS_PER_CHUNK
        chunks = group_words_into_chunks(words, words_per_chunk=words_per_chunk)
        subtitle_clips = create_subtitle_clips(chunks, y_pos=caption_y, font_size=vid_font_size if video_format == "short" else int(vid_font_size * 0.7), content_type=content_type)
        print(f"  Created {len(subtitle_clips)} subtitle clips "
              f"from {len(words)} words ({words_per_chunk} words/chunk) "
              f"at y={caption_y}px, font={vid_font_size}px, style={content_type}")

    # --- Fake Text Chat Bubbles ---
    bubble_clips = []
    if content_type == "fake_text" and messages:
        print("  Generating chat bubbles...")
        bubble_clips = create_chat_bubble_clips(messages, audio_duration)

    # --- Pop-up Image (for Quiz answers) ---
    popup_clips = []
    if popup_image_path and popup_trigger_word and words:
        from moviepy.editor import ImageClip
        trigger_lower = popup_trigger_word.lower()
        popup_start = None
        for w in words:
            if trigger_lower in w['text'].lower():
                popup_start = w['start']
                break
        
        if popup_start is not None and os.path.exists(popup_image_path):
            img = ImageClip(popup_image_path)
            
            # Make it slightly smaller to leave room for the border
            img = img.resize(width=int(VIDEO_WIDTH * 0.75))
            
            # Add a stylish thick white border (like a polaroid/card)
            from moviepy.video.fx.all import margin
            img = img.margin(color=(255, 255, 255), top=15, bottom=15, left=15, right=15)
            
            # Add a slow, continuous zoom-in effect to keep it dynamic
            def popup_zoom(t):
                # t goes from 0 to its duration
                # Zoom from 1.0x to 1.05x
                progress = t / max(audio_duration, 0.1)
                return 1.0 + (0.05 * progress)
            img = img.resize(popup_zoom)

            img = img.set_position(('center', 'center'))
            img = img.set_start(popup_start)
            img = img.set_end(audio_duration)
            
            # Smooth fade in over 0.25 seconds
            img = img.crossfadein(0.25)
            
            popup_clips.append(img)
            print(f"  🖼️ Added pop-up image at {popup_start:.2f}s (triggered by '{popup_trigger_word}') with stylish border & fade-in")

    # --- Hook Card (pre-roll text overlay) ---
    # Displays the headline as a bold text card for 1.2s BEFORE the voiceover,
    # giving the viewer a reason to stop scrolling and stay.
    # The hook card is layered ON TOP of the background video (which is already playing)
    # so there's visual movement behind the text — not a static black screen.
    hook_clips = []
    if hook_text:
        hook_clips, hook_dur = create_hook_card(hook_text, content_type=content_type)
        if hook_clips:
            # Shift ALL audio and subtitles forward by hook_dur so the voiceover
            # starts AFTER the hook card fades out
            from moviepy.audio.AudioClip import AudioClip as _AudioClipBase
            
            # Create silence for the hook card duration
            silence_dur = hook_dur
            silence = ColorClip(size=(1, 1), color=(0, 0, 0)).set_duration(silence_dur)
            # We don't actually use silence as a clip — we shift the audio instead
            
            # Shift the mixed audio forward
            if mixed_audio is not None:
                # Pad the beginning with silence by creating a delayed version
                from moviepy.audio.AudioClip import AudioArrayClip
                silence_samples = int(44100 * silence_dur)
                silence_array = np.zeros((silence_samples, 2))
                silence_audio = AudioArrayClip(silence_array, fps=44100)
                mixed_audio = CompositeAudioClip([silence_audio, mixed_audio.set_start(silence_dur)])
            
            # Re-attach the shifted audio
            # Extend the background video to account for the hook card
            total_duration = audio_duration + hook_dur
            video_with_audio = bg_clip.set_duration(total_duration).set_audio(mixed_audio)
            
            # Shift all subtitle clips forward by hook_dur
            shifted_subs = []
            for clip in subtitle_clips:
                original_start = clip.start
                original_end = clip.end
                shifted = clip.set_start(original_start + hook_dur).set_end(original_end + hook_dur)
                shifted_subs.append(shifted)
            subtitle_clips = shifted_subs
            
            # Shift bubble clips forward too
            shifted_bubbles = []
            for clip in bubble_clips:
                original_start = clip.start
                original_end = clip.end
                shifted = clip.set_start(original_start + hook_dur).set_end(original_end + hook_dur)
                shifted_bubbles.append(shifted)
            bubble_clips = shifted_bubbles
            
            # Shift popup clips forward
            shifted_popups = []
            for clip in popup_clips:
                original_start = clip.start
                original_end = clip.end
                shifted = clip.set_start(original_start + hook_dur).set_end(original_end + hook_dur)
                shifted_popups.append(shifted)
            popup_clips = shifted_popups

    # --- Composite Everything ---
    print("  Compositing layers...")
    all_clips = [video_with_audio] + bubble_clips + popup_clips + subtitle_clips + hook_clips
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
