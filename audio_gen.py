import os
import sys
import random
import asyncio
import edge_tts
from edge_tts import SubMaker

# Fix Windows console encoding for emoji in log output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Voice pool — rotating voices prevents audience fatigue and adds variety.
# More voices = less channel fatigue, harder for YouTube to flag as automated.
# Each tuple is (voice_name, description)
VOICE_POOL = [
    ("en-GB-RyanNeural", "Natural male storyteller"),
    ("en-US-AriaNeural", "Engaging female narrator"),
    ("en-US-GuyNeural", "Conversational male voice"),
    ("en-US-ChristopherNeural", "Deep authoritative male"),
    ("en-US-JennyNeural", "Warm friendly female"),
]

# Inspiration voice pool — deeper, calmer, more authoritative voices
# for Dark Stoic / motivational content. No female voices (matches the dark monk aesthetic).
INSPIRATION_VOICE_POOL = [
    ("en-US-GuyNeural", "Deep calm male — stoic authority"),
    ("en-US-ChristopherNeural", "Warm baritone — philosophical depth"),
    ("en-GB-RyanNeural", "British authority — timeless wisdom"),
]

# Slightly slower than the old +15% — gives the narration more weight and drama, preventing monotonic delivery
TTS_RATE = "+10%"

# Slower rate for inspiration — deliberate, contemplative pacing
INSPIRATION_TTS_RATE = "+5%"

# Would You Rather — energetic, engaging voices
WYR_VOICE_POOL = [
    ("en-US-AriaNeural", "Energetic female — quiz show host feel"),
    ("en-US-GuyNeural", "Upbeat conversational male"),
    ("en-US-JennyNeural", "Warm friendly narrator"),
]
WYR_TTS_RATE = "+15%"  # Faster = more energy

# Fake Text — conversational, casual voices
FAKE_TEXT_VOICE_POOL = [
    ("en-US-JennyNeural", "Casual female storyteller"),
    ("en-US-AriaNeural", "Expressive dramatic female"),
    ("en-US-GuyNeural", "Casual male narrator"),
]
FAKE_TEXT_TTS_RATE = "+10%"

# Dark Psychology — authoritative, mysterious voices
DARK_PSYCH_VOICE_POOL = [
    ("en-US-ChristopherNeural", "Deep authoritative — professor feel"),
    ("en-GB-RyanNeural", "British authority — intellectual"),
    ("en-US-GuyNeural", "Calm knowledgeable male"),
]
DARK_PSYCH_TTS_RATE = "+5%"  # Slower = more gravitas

# True Crime — eerie, whispery voices at slow pace
TRUE_CRIME_VOICE_POOL = [
    ("en-US-ChristopherNeural", "Deep ominous narrator"),
    ("en-GB-RyanNeural", "British suspense — documentary feel"),
    ("en-US-GuyNeural", "Low calm male — unsettling"),
]
TRUE_CRIME_TTS_RATE = "+0%"  # Slowest = maximum dread


async def _generate(text, output_mp3, output_srt, voice, rate):
    """
    Internal async function that streams audio from edge-tts while capturing
    WordBoundary events for exact word-level subtitle timing.
    """
    communicate = edge_tts.Communicate(
        text, voice,
        rate=rate,
        boundary="WordBoundary"  # Word-level timing (not sentence-level)
    )
    submaker = SubMaker()

    with open(output_mp3, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])

    # Save word-level SRT subtitles
    srt_content = submaker.get_srt()
    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return srt_content


def generate_audio_and_subs(text, output_mp3="temp/audio.mp3", output_srt="temp/subs.srt", voice=None, content_type="story"):
    """
    Uses edge-tts Python API to generate a realistic voiceover with
    exact word-level subtitle timing (via WordBoundary events).

    This replaces the old CLI approach that only produced sentence-level timing.

    Args:
        text: The script to narrate.
        output_mp3: Path to save the audio file.
        output_srt: Path to save the SRT subtitle file (word-level).
        voice: Optional specific voice name. If None, picks randomly from pool.
        content_type: 'story', 'inspiration', 'would_you_rather', 'fake_text',
                      'dark_psychology', or 'true_crime' — selects voice pool and TTS rate.

    Returns:
        Tuple of (mp3_path, srt_path) or (None, None) on failure.
    """
    print("Generating audio and subtitles...")

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_mp3), exist_ok=True)

    # Select voice pool and TTS rate based on content type
    if content_type == "inspiration":
        pool = INSPIRATION_VOICE_POOL
        rate = INSPIRATION_TTS_RATE
    elif content_type == "would_you_rather":
        pool = WYR_VOICE_POOL
        rate = WYR_TTS_RATE
    elif content_type == "fake_text":
        pool = FAKE_TEXT_VOICE_POOL
        rate = FAKE_TEXT_TTS_RATE
    elif content_type == "dark_psychology":
        pool = DARK_PSYCH_VOICE_POOL
        rate = DARK_PSYCH_TTS_RATE
    elif content_type == "true_crime":
        pool = TRUE_CRIME_VOICE_POOL
        rate = TRUE_CRIME_TTS_RATE
    else:
        pool = VOICE_POOL
        rate = TTS_RATE

    # Pick a voice
    if voice is None:
        chosen_voice, voice_desc = random.choice(pool)
        print(f"  Voice: {chosen_voice} ({voice_desc})")
    else:
        chosen_voice = voice
        print(f"  Voice: {chosen_voice}")

    try:
        srt_content = asyncio.run(
            _generate(text, output_mp3, output_srt, chosen_voice, rate)
        )

        # Count words for logging
        word_count = len(srt_content.strip().split('\n\n'))
        print(f"  ✅ Audio and word-level subtitles generated! ({word_count} word cues)")
        return output_mp3, output_srt
    except Exception as e:
        print(f"  ❌ Error generating audio: {e}")
        return None, None


if __name__ == "__main__":
    mp3, srt = generate_audio_and_subs(
        "This is a test of the automatic video generation pipeline. Subscribe for more."
    )
    if srt:
        with open(srt, 'r', encoding='utf-8') as f:
            print("\nSRT Preview:")
            lines = f.read().strip().split('\n')
            for line in lines[:30]:
                print(f"  {line}")
