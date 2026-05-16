import os
import subprocess

def generate_audio_and_subs(text, output_mp3="temp/audio.mp3", output_vtt="temp/subs.vtt"):
    """
    Uses edge-tts to generate a realistic voiceover and word-level subtitles.
    """
    print("Generating audio and subtitles...")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_mp3), exist_ok=True)
    
    # en-US-ChristopherNeural is a good, deep male voice suitable for stories.
    # en-GB-SoniaNeural is a good female alternative.
    voice = "en-US-ChristopherNeural"
    
    # We write the text to a temporary file because passing long strings via CLI can break on Windows
    temp_text_file = "temp/script.txt"
    with open(temp_text_file, "w", encoding="utf-8") as f:
        f.write(text)
        
    command = [
        "edge-tts",
        "--file", temp_text_file,
        "--write-media", output_mp3,
        "--write-subtitles", output_vtt,
        "--voice", voice,
        "--rate", "+15%"
    ]
    
    try:
        # Run the command and capture output
        subprocess.run(command, check=True, capture_output=True, text=True)
        print("Audio and subtitles generated successfully!")
        return output_mp3, output_vtt
    except subprocess.CalledProcessError as e:
        print(f"Error generating audio: {e.stderr}")
        return None, None

if __name__ == "__main__":
    generate_audio_and_subs("This is a test of the automatic video generation pipeline. Subscribe for more.")
