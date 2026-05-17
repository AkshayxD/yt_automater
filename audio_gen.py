import os
import random
import subprocess

# Voice pool — rotating voices prevents audience fatigue and adds variety
# Each tuple is (voice_name, description)
VOICE_POOL = [
    ("en-GB-RyanNeural", "Natural male storyteller"),
    ("en-US-AriaNeural", "Engaging female narrator"),
    ("en-US-GuyNeural", "Conversational male voice"),
]

# Slightly slower than the old +15% — gives the narration more weight and drama
TTS_RATE = "+10%"


def generate_audio_and_subs(text, output_mp3="temp/audio.mp3", output_vtt="temp/subs.vtt", voice=None):
    """
    Uses edge-tts to generate a realistic voiceover and word-level subtitles.

    Args:
        text: The script to narrate.
        output_mp3: Path to save the audio file.
        output_vtt: Path to save the VTT subtitle file.
        voice: Optional specific voice name. If None, picks randomly from VOICE_POOL.

    Returns:
        Tuple of (mp3_path, vtt_path) or (None, None) on failure.
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

    # We write the text to a temporary file because passing long strings
    # via CLI can break on Windows
    temp_text_file = "temp/script.txt"
    with open(temp_text_file, "w", encoding="utf-8") as f:
        f.write(text)

    command = [
        "edge-tts",
        "--file", temp_text_file,
        "--write-media", output_mp3,
        "--write-subtitles", output_vtt,
        "--voice", chosen_voice,
        "--rate", TTS_RATE
    ]

    try:
        # Run the command and capture output
        subprocess.run(command, check=True, capture_output=True, text=True)
        print("  ✅ Audio and subtitles generated successfully!")
        return output_mp3, output_vtt
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error generating audio: {e.stderr}")
        return None, None
    except FileNotFoundError:
        print("  ❌ edge-tts not found. Install it with: pip install edge-tts")
        return None, None


if __name__ == "__main__":
    generate_audio_and_subs(
        "This is a test of the automatic video generation pipeline. Subscribe for more."
    )
