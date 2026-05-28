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

# Slightly slower than the old +15% — gives the narration more weight and drama, preventing monotonic delivery
TTS_RATE = "+10%"


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


def generate_audio_and_subs(text, output_mp3="temp/audio.mp3", output_srt="temp/subs.srt", voice=None):
    """
    Uses edge-tts Python API to generate a realistic voiceover with
    exact word-level subtitle timing (via WordBoundary events).

    This replaces the old CLI approach that only produced sentence-level timing.

    Args:
        text: The script to narrate.
        output_mp3: Path to save the audio file.
        output_srt: Path to save the SRT subtitle file (word-level).
        voice: Optional specific voice name. If None, picks randomly from VOICE_POOL.

    Returns:
        Tuple of (mp3_path, srt_path) or (None, None) on failure.
    """
    print("Generating audio and subtitles...")

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_mp3), exist_ok=True)

    # Pick a voice
    if voice is None:
        chosen_voice, voice_desc = random.choice(VOICE_POOL)
        print(f"  Voice: {chosen_voice} ({voice_desc})")
    else:
        chosen_voice = voice
        print(f"  Voice: {chosen_voice}")

    try:
        srt_content = asyncio.run(
            _generate(text, output_mp3, output_srt, chosen_voice, TTS_RATE)
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
