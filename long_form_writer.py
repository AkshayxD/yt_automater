"""
Long-Form Video Script Writer

Uses Google Gemini to generate a 5-8 minute video essay (500-1000 words)
and 10-15 highly detailed visual prompts to be used for the Ken Burns image slideshow.

Topics rotate around Dark Psychology and History.
"""
import os
import sys
import json
import random
import requests

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

LONG_FORM_TOPICS = [
    "The Dark Psychology of Cult Leaders (How they manipulate masses)",
    "The History of the CIA's MKUltra Mind Control Experiments",
    "The True Story of the Stanford Prison Experiment (And why it was flawed)",
    "How Casinos Use Dark Psychology to Keep You Gambling",
    "The Grey Rock Method: The Ultimate Defense Against Narcissists",
    "The Deadliest Mistakes in Human History",
    "The Psychology of Serial Killers: Nature vs Nurture",
    "The Most Disturbing Unsolved Mysteries in History",
    "How Social Media Algorithms Brainwash You (The Science)",
    "The 48 Laws of Power: Deconstructed and Explained",
]

SYSTEM_PROMPT = """You are an elite, viral YouTube video essay writer.
Your job is to write a highly engaging, 5-8 minute long-form video essay (700-1000 words).

STRUCTURE:
1. HOOK (0:00-0:30): Start with a shocking statement, mystery, or mind-blowing fact. Do NOT introduce yourself. Hook the viewer immediately.
2. THE SETUP (0:30-2:00): Explain the context, introduce the characters or psychological principles.
3. THE DEEP DIVE (2:00-6:00): The core meat of the video. Use 2-3 specific real-world examples or historical stories to prove the point.
4. THE CLIMAX (6:00-7:30): The shocking twist, resolution, or final disturbing revelation.
5. ENGAGEMENT CTA (7:30-8:00): "What do you think? Let me know in the comments and hit that subscribe button if you enjoyed this deep dive."

PACING:
Use short, punchy paragraphs. Inject 1-2 second pauses between major concepts by using ellipses (...) or explicitly stating [PAUSE].
The TTS voice will read this, so write exactly how it should be spoken. No emojis in the spoken text.

VISUAL PROMPTS:
To make the video dynamic, you must also generate 10 to 15 highly detailed visual prompts that match the script's progression.
These prompts will be fed to an AI image generator to create the video's visuals.
Make them descriptive, cinematic, and moody (e.g., "A cinematic, dark, moody 3D render of a person standing alone in a misty forest at night").

Respond ONLY with a valid JSON object in this exact format:
{
  "headline": "A punchy ALL CAPS title (5-10 words). Example: 'THE DARK PSYCHOLOGY OF CULTS'",
  "script": "The full spoken script (700-1000 words) with the structure above.",
  "visual_prompts": [
    "Prompt 1...",
    "Prompt 2...",
    "..."
  ]
}"""

def generate_script():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  ❌ GEMINI_API_KEY not found. Returning fallback script.")
        return get_fallback_script()

    topic = random.choice(LONG_FORM_TOPICS)
    print(f"  📝 Generating Long-Form script via Gemini API. Topic: {topic}")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Write a video essay about: {topic}"}]
        }],
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "generationConfig": {
            "temperature": 0.8,
            "response_mime_type": "application/json",
        }
    }

    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        data = response.json()
        
        text_response = data['candidates'][0]['content']['parts'][0]['text']
        script_data = json.loads(text_response)
        
        # Add metadata
        script_data['topic'] = topic
        return script_data
        
    except Exception as e:
        print(f"  ❌ Error calling Gemini API: {e}")
        try:
            print(f"  Response was: {response.text}")
        except:
            pass
        return get_fallback_script()

def get_fallback_script():
    return {
        "headline": "THE PSYCHOLOGY OF ISOLATION",
        "script": "This is a fallback long-form script. Imagine 700 words here explaining dark psychology. [PAUSE] Let me know what you think in the comments and subscribe for more.",
        "visual_prompts": [
            "A cinematic dark room with a single glowing light bulb",
            "A silhouette of a person standing in a massive, empty hallway",
            "A close up of a ticking clock in a dark room"
        ],
        "topic": "Fallback"
    }

if __name__ == "__main__":
    res = generate_script()
    print("\n--- GENERATED LONG-FORM SCRIPT ---")
    print(f"Headline: {res.get('headline')}")
    print(f"Word count: {len(res.get('script', '').split())}")
    print(f"Images: {len(res.get('visual_prompts', []))}")
