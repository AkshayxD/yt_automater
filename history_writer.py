"""
History Writer — Scrapes Wikipedia "On This Day" API and generates dramatic shorts.

Features:
1. Scrapes events for current day (month/day)
2. Selects the most dramatic/compelling event (conflict, disaster, discovery)
3. Fetches Wikipedia's thumbnail/image and saves it locally
4. Uses Gemini 2.5 Flash to rewrite the story into a high-retention vertical script
"""
import os
import sys
import json
import urllib.request
import urllib.parse
import random
from datetime import datetime

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """You are a viral history creator. You turn dry historical records into heart-stopping, dramatic stories that viewers cannot scroll past.

Your goal: Make the historical event feel like it's happening in real-time, focusing on the suspense, irony, or sheer magnitude of the moment.

THE PERFECT HISTORY SCRIPT STRUCTURE:
1. HOOK (1 sentence): Start at the climax. No intro. First word must be a dramatic verb, name, or year — NEVER "On this day", "Did you know", "In history".
   Good openers: "Hitler and Stalin signed a secret deal that doomed Europe.", "A nuclear warhead accidentally fell on North Carolina.", "Smallpox was officially declared dead."
2. THE EVENTS (3-4 sentences): Build the scene. Introduce the key people, the high stakes, and what went wrong or succeeded.
3. THE AFTERMATH (1 sentence): State the consequence or final death toll/impact.
4. SUBSCRIBE CTA: Rotate styles: "Subscribe for more dark history.", "Hit that subscribe button if you would have survived.", "Subscribe so you don't miss tomorrow's story."

RULES:
1. 80-100 words EXACTLY.
2. Adapt the tone to the event. If it's a disaster, sound grave. If it's an invention, sound amazed.
3. Make it visceral: use words for sights, sounds, feelings (cold, fire, screams, silence).
4. Short sentences (under 13 words max).
5. NO emojis, NO markdown, NO brackets. Only spoken voiceover text.
"""

USER_PROMPT_TEMPLATE = """Transform this historical record into a viral narration script.

Historical Year: {year}
Core Event Description: {description}

Respond ONLY with valid JSON:
{{
  "headline": "A punchy ALL CAPS title (5-8 words). Example: 'THE DAY AN ATOMBOMB DROPPED ON USA'",
  "script": "The 80-100 word script following the structure (HOOK → EVENTS → AFTERMATH → SUBSCRIBE CTA). Starts dramatic."
}}"""


def get_history_event_from_wikipedia(month=None, day=None, used_themes=None):
    """
    Fetches events from Wikipedia On This Day API and filter-selects the most dramatic one.
    """
    if month is None or day is None:
        now = datetime.now()
        month = now.month
        day = now.day

    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}"
    headers = {"User-Agent": "YTShorthotbot/1.0 (contact: test@example.com) Python-urllib"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        events = data.get("events", [])
        if not events:
            return None

        # Filter events to find the most dramatic one
        # Keywords suggesting conflict, crime, explosion, space, survival, etc.
        dramatic_keywords = ["assassin", "kill", "die", "death", "bomb", "war", "battle", "disaster",
                             "accident", "collapse", "execut", "arrest", "attack", "murder", "sink", "fire",
                             "invent", "space", "launch", "nuclear", "stole", "robbed"]

        scored_events = []
        for index, e in enumerate(events):
            text = e.get("text", "").lower()
            year = e.get("year", 0)

            # Skip if theme used recently
            theme_id = f"{year}_{text[:30]}"
            if used_themes and theme_id in used_themes:
                continue

            score = 0
            for kw in dramatic_keywords:
                if kw in text:
                    score += 5

            # Favor more modern events (1800+) since we have better images/footage
            if year > 1950:
                score += 3
            elif year > 1800:
                score += 2

            scored_events.append((score, index, e))

        # Sort by score descending
        scored_events.sort(key=lambda x: x[0], reverse=True)

        if scored_events:
            best_event = scored_events[0][2]
            return best_event

    except Exception as e:
        print(f"  ⚠️ Wikipedia scrape failed: {e}")

    return None


def download_wikipedia_image(event, temp_dir="temp"):
    """
    Downloads the primary image from Wikipedia page if available.
    """
    os.makedirs(temp_dir, exist_ok=True)
    pages = event.get("pages", [])
    if not pages:
        return None

    for page in pages:
        originalimage = page.get("originalimage", {})
        img_url = originalimage.get("source")
        if img_url:
            # Check file extension (only supports common formats)
            ext = img_url.split('.')[-1].lower().split('?')[0]
            if ext in ['jpg', 'jpeg', 'png']:
                img_path = os.path.join(temp_dir, f"history_event.{ext}")
                try:
                    headers = {"User-Agent": "YTShorthotbot/1.0 (contact: test@example.com) Python-urllib"}
                    req = urllib.request.Request(img_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as response, open(img_path, 'wb') as out_file:
                        out_file.write(response.read())
                    print(f"  📸 Downloaded historical image: {os.path.basename(img_path)} ({originalimage.get('width')}x{originalimage.get('height')})")
                    return img_path
                except Exception as ex:
                    print(f"  ⚠️ Image download failed: {ex}")

    return None


def generate_history_script(used_themes=None):
    """
    Main runner: scrapes Wikipedia, fetches image, and rewrites via Gemini.

    Returns:
        tuple: (headline, script, image_path, year, theme_id)
    """
    now = datetime.now()
    event = get_history_event_from_wikipedia(now.month, now.day, used_themes)

    if not event:
        print("  ⚠️ No event found on Wikipedia, using fallback")
        return generate_fallback_history()

    year = event.get("year", 1900)
    desc = event.get("text", "")
    theme_id = f"{year}_{desc[:30]}"

    # Download thumbnail
    image_path = download_wikipedia_image(event)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  ⚠️ GEMINI_API_KEY not found! Using fallback rewriting.")
        # Local rewrite fallback
        headline = f"HISTORY IN {year}"
        script = f"{desc}. Was this one of the most important moments in history? Let me know below."
        return headline, script, image_path, year, theme_id

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = USER_PROMPT_TEMPLATE.format(year=year, description=desc)

        print(f"  📰 Rewriting historical event from {year}...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.9,
                "max_output_tokens": 400,
                "response_mime_type": "application/json",
            }
        )

        result_text = response.text.strip()

        # Clean markdown
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        elif result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        data = json.loads(result_text)
        headline = data.get("headline", f"HISTORICAL ERROR {year}").strip().strip('"\'')
        script = data.get("script", "").strip()

        # Simple verification of hook
        script_words = script.split()
        if script_words and script_words[0].lower() in ["on", "in", "did", "this", "yesterday", "recently"]:
            print(f"  ⚠️ AI generated a weak history hook: '{script_words[0]}' - replacing opening word")
            # Restructure hook slightly if it starts with "in/on"
            if script_words[0].lower() in ["on", "in"] and len(script_words) > 1:
                script = ' '.join(script_words[1:])
                script = script[0].upper() + script[1:]

        # Validate count
        word_count = len(script.split())
        if word_count > 110:
            words = script.split()
            script = ' '.join(words[:90])
            for punct in ['.', '!', '?']:
                last_idx = script.rfind(punct)
                if last_idx > len(script) * 0.7:
                    script = script[:last_idx + 1]
                    break

        print(f"  ✅ History template compiled!")
        print(f"     Headline: {headline}")
        print(f"     Year: {year}")
        print(f"     Words: {len(script.split())}")

        return headline, script, image_path, year, theme_id

    except Exception as e:
        print(f"  ⚠️ Gemini failed: {e} - using simple description")
        return f"HISTORY IN {year}", f"{desc}. Rate this event 1 to 10 in the comments below.", image_path, year, theme_id


def generate_fallback_history():
    """Fallback if Wikipedia/scraping fails completely."""
    return (
        "THE ATOM BOMB ERROR THAT ALMOST DESTROYED USA",
        "A nuclear warhead accidentally plummeted from a B-52 bomber onto North Carolina. The bomb fell five miles, hit the ground, and went through five of its six detonation steps. A single low-voltage switch was the only thing preventing a thermonuclear blast. Would you have survived? Comment below.",
        None,
        1961,
        "1961_nuke_nc"
    )


if __name__ == "__main__":
    headline, script, image, year, theme = generate_history_script()
    print(f"\n--- SCRAPED RESULT ---")
    print(f"YEAR: {year}")
    print(f"THEME ID: {theme}")
    print(f"HEADLINE: {headline}")
    print(f"IMAGE: {image}")
    print(f"SCRIPT_TEXT: \n{script}")
