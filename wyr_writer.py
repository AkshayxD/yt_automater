"""
Would You Rather Script Writer — Generates polarizing WYR scripts for YouTube Shorts.

Uses Google Gemini 2.5 Flash (free tier: 15 RPM, 1500 RPD) to create:
1. A bold, curiosity-driven headline (ALL CAPS, 4-8 words)
2. A Hook → Option A → Option B → Comment Bait structure
3. Designed to maximize comment engagement (viewers MUST pick a side)

Content is 100% original — AI-generated hypothetical scenarios.
No scraping needed. Pure AI generation with rotating themes.

Requires: GEMINI_API_KEY environment variable
Fallback: Returns a pre-written fallback script if API is unavailable
"""
import os
import sys
import re
import json
import random

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# --- WYR Theme Bank ---
# 30 rotating themes to prevent repetition across days.
# Each theme has the core dilemma and two vivid options.
WYR_THEMES = [
    {"theme": "Know Death Date vs Cause", "dilemma": "Would you rather know the exact date of your death, or the cause?", "tags": ["existential", "dark"]},
    {"theme": "Read Minds vs Invisible", "dilemma": "Would you rather be able to read everyone's thoughts, or be invisible whenever you want?", "tags": ["superpower", "fun"]},
    {"theme": "Relive One Day vs Skip One Year", "dilemma": "Would you rather relive the best day of your life forever, or skip ahead one year right now?", "tags": ["time", "philosophical"]},
    {"theme": "Never Lie vs Never Be Lied To", "dilemma": "Would you rather never be able to lie again, or never be lied to again?", "tags": ["social", "deep"]},
    {"theme": "Know Every Language vs Play Every Instrument", "dilemma": "Would you rather speak every language fluently, or play every instrument perfectly?", "tags": ["talent", "fun"]},
    {"theme": "10M Dollars vs Start Over at 10", "dilemma": "Would you rather get 10 million dollars right now, or go back to age 10 with all your current knowledge?", "tags": ["money", "time"]},
    {"theme": "No Phone vs No Friends", "dilemma": "Would you rather give up your phone forever, or give up all your friends?", "tags": ["social", "modern"]},
    {"theme": "Always Cold vs Always Hot", "dilemma": "Would you rather always feel freezing cold, or always feel burning hot?", "tags": ["physical", "fun"]},
    {"theme": "Live 1000 Years vs 10 Lives", "dilemma": "Would you rather live one life for 1000 years, or live 10 different lives of 80 years each?", "tags": ["existential", "deep"]},
    {"theme": "Know Future vs Change Past", "dilemma": "Would you rather see 10 minutes into the future, or change 10 minutes of your past?", "tags": ["time", "power"]},
    {"theme": "No Sleep vs No Food", "dilemma": "Would you rather never need to sleep again, or never need to eat again?", "tags": ["physical", "practical"]},
    {"theme": "Fly Slowly vs Run Fast", "dilemma": "Would you rather fly but only at walking speed, or run at 200mph but never fly?", "tags": ["superpower", "fun"]},
    {"theme": "Everyone Hears Thoughts vs Everyone Sees Dreams", "dilemma": "Would you rather have everyone hear your thoughts, or everyone see your dreams?", "tags": ["embarrassing", "social"]},
    {"theme": "Rich and Hated vs Poor and Loved", "dilemma": "Would you rather be the richest person alive but universally hated, or broke but loved by everyone?", "tags": ["money", "social"]},
    {"theme": "Perfect Memory vs Forget Pain", "dilemma": "Would you rather remember everything perfectly, or forget every painful memory?", "tags": ["mental", "deep"]},
    {"theme": "Control Time vs Control Weather", "dilemma": "Would you rather control time, or control the weather?", "tags": ["superpower", "power"]},
    {"theme": "Know How Everyone Dies vs When", "dilemma": "Would you rather know how everyone you meet will die, or when they will die?", "tags": ["dark", "existential"]},
    {"theme": "Only Whisper vs Only Shout", "dilemma": "Would you rather only be able to whisper, or only be able to shout?", "tags": ["funny", "social"]},
    {"theme": "No Music vs No Movies", "dilemma": "Would you rather live without music forever, or live without movies and TV forever?", "tags": ["entertainment", "tough"]},
    {"theme": "Always Tell Truth vs Always Lie", "dilemma": "Would you rather be forced to always tell the truth, or forced to always lie?", "tags": ["social", "philosophical"]},
    {"theme": "Live In Past vs Live In Future", "dilemma": "Would you rather live 200 years in the past, or 200 years in the future?", "tags": ["time", "adventure"]},
    {"theme": "Endless Money vs Endless Time", "dilemma": "Would you rather have unlimited money but only 5 years to live, or be broke but live to 150?", "tags": ["money", "existential"]},
    {"theme": "Read Every Book vs Travel Everywhere", "dilemma": "Would you rather have read every book ever written, or have visited every country on Earth?", "tags": ["knowledge", "adventure"]},
    {"theme": "No One Attends Wedding vs Funeral", "dilemma": "Would you rather have no one attend your wedding, or no one attend your funeral?", "tags": ["dark", "social"]},
    {"theme": "Speak to Animals vs Speak All Languages", "dilemma": "Would you rather speak to animals, or speak every human language?", "tags": ["superpower", "fun"]},
    {"theme": "Lose All Memories vs Never Make New Ones", "dilemma": "Would you rather lose all your memories, or never be able to make new ones?", "tags": ["mental", "dark"]},
    {"theme": "Be Famous vs Be Powerful", "dilemma": "Would you rather be world-famous but powerless, or unknown but the most powerful person alive?", "tags": ["power", "social"]},
    {"theme": "Know Everything vs Be Lucky", "dilemma": "Would you rather know everything but be unlucky, or know nothing but be incredibly lucky?", "tags": ["philosophical", "fun"]},
    {"theme": "Rewind 10 Seconds vs Pause 10 Seconds", "dilemma": "Would you rather rewind the last 10 seconds of your life anytime, or pause time for 10 seconds anytime?", "tags": ["time", "superpower"]},
    {"theme": "Everyone Forget You vs You Forget Everyone", "dilemma": "Would you rather have everyone forget who you are, or forget everyone you've ever known?", "tags": ["dark", "social"]},
]

# System prompt optimized for Would You Rather scripts
WYR_SYSTEM_PROMPT = """You are the #1 viral "Would You Rather" YouTube Shorts scriptwriter. Your videos consistently hit 5M+ views because they're IMPOSSIBLE to scroll past — viewers MUST pick a side and comment.

YOUR STYLE: Energetic, provocative, mind-bending. You present each option as if it's the obvious choice — then flip it. Your tone is "best friend asking you an impossible question at 2 AM."

THE PERFECT SCRIPT STRUCTURE:

1. HOOK (1 sentence, 0-3 seconds): Present the dilemma immediately. "Would you rather..." — drop the viewer straight into the choice. Make it sound impossible. NEVER open with "Hey guys" or "Today we're asking...".

2. OPTION A DEEP-DIVE (2-3 sentences, 3-15 seconds): Describe Option A vividly. Start with why it sounds amazing, then reveal the hidden downside. Use "Think about it..." or "Imagine..." to make it personal.

3. OPTION B DEEP-DIVE (2-3 sentences, 15-28 seconds): Same treatment for Option B. Make it sound equally tempting AND equally terrifying. The viewer should be genuinely torn.

4. THE TWIST (1 sentence, optional): Add a surprising angle neither option covers. "But here's what nobody considers..."

5. COMMENT BAIT (1 sentence, 28-35 seconds): Force the viewer to comment. Rotate between: "Comment A or B — I need to know.", "Type 1 or 2 right now.", "I went with A. Fight me in the comments.", "This one DESTROYED my friend group. Which side are you on?"

CRITICAL RULES:
1. 80-100 words EXACTLY. Every word must earn its place.
2. NO AI clichés: Never use "In a world where...", "Let that sink in", "Here's the thing".
3. MAKE IT PERSONAL: Use "you" constantly. "Imagine YOU wake up and..." not "Imagine someone wakes up..."
4. VIVID CONSEQUENCES: Don't just state the option — paint the picture of living with it.
5. NO EMOJIS, NO BRACKETS, NO MARKDOWN: Pure spoken text only.
6. PROPER APOSTROPHES: Always write "don't" not "dont", "you're" not "youre".
7. CONVERSATIONAL TONE: Contractions, fragments, rhetorical questions. Sound human."""

WYR_USER_PROMPT = """Write a viral "Would You Rather" YouTube Shorts script about this dilemma:

DILEMMA: {dilemma}
THEME: {theme}

Respond ONLY with a valid JSON object:
{{
  "headline": "A punchy ALL CAPS title (4-8 words). Examples: 'WOULD YOU RATHER KNOW WHEN YOU DIE', 'THIS CHOICE WILL BREAK YOU'",
  "script": "The full spoken script (80-100 words). Dilemma → Option A → Option B → Comment bait.",
  "option_a": "Brief label for Option A (2-5 words)",
  "option_b": "Brief label for Option B (2-5 words)"
}}"""


def get_unused_theme(used_themes=None):
    """
    Picks a WYR theme that hasn't been used recently.

    Args:
        used_themes: List of recently used theme names to avoid

    Returns:
        dict with 'theme', 'dilemma', 'tags' keys
    """
    if not used_themes:
        return random.choice(WYR_THEMES)

    # Filter out recently used themes
    available = [t for t in WYR_THEMES if t["theme"] not in used_themes]

    if not available:
        # All themes used — reset and pick any
        print("  ♻️ All WYR themes exhausted — resetting rotation")
        available = WYR_THEMES

    return random.choice(available)


def generate_wyr_script(used_themes=None):
    """
    Generates a Would You Rather script using Gemini AI.

    Args:
        used_themes: List of recently used theme names to avoid repetition

    Returns:
        tuple: (headline, script, option_a, option_b, theme_name)
        Falls back to a pre-written script if API is unavailable
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    # Pick a fresh theme
    theme = get_unused_theme(used_themes)
    theme_name = theme["theme"]
    print(f"  🎯 Selected WYR theme: \"{theme_name}\"")

    if not api_key:
        print("  ⚠️ GEMINI_API_KEY not found! Using fallback script.")
        return _get_fallback_script(theme)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = WYR_USER_PROMPT.format(
            dilemma=theme["dilemma"],
            theme=theme["theme"]
        )

        print("  🤖 Generating WYR script with Gemini 2.5 Flash...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": WYR_SYSTEM_PROMPT,
                "temperature": 1.0,  # High creativity for fun scenarios
                "max_output_tokens": 400,
                "response_mime_type": "application/json",
            }
        )

        result_text = response.text.strip()

        # Clean markdown code blocks if Gemini returns them
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        elif result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        try:
            data = json.loads(result_text)
            headline = data.get("headline", theme_name.upper()).strip()
            script = data.get("script", "").strip()
            option_a = data.get("option_a", "Option A").strip()
            option_b = data.get("option_b", "Option B").strip()

            if not script:
                print("  ⚠️ AI returned empty script! Using fallback.")
                return _get_fallback_script(theme)
        except json.JSONDecodeError as e:
            print(f"  ⚠️ Failed to parse JSON: {e}, using fallback")
            print(f"  Raw response: {result_text[:200]}")
            return _get_fallback_script(theme)

        # Clean up formatting
        headline = re.sub(r'[*#_]', '', headline).strip('"').strip("'")
        script = re.sub(r'[*#_]', '', script)

        # Validate word count — target 80-100 words
        word_count = len(script.split())
        if word_count > 115:
            words = script.split()
            trimmed = ' '.join(words[:100])
            boundaries = [trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?')]
            last_boundary = max(boundaries)
            if last_boundary > int(len(trimmed) * 0.7):
                script = trimmed[:last_boundary + 1]
            else:
                script = trimmed
            print(f"  ⚠️ Script was {word_count} words — trimmed to {len(script.split())}")

        print(f"  ✅ WYR script generated!")
        print(f"     Headline: \"{headline}\"")
        print(f"     Option A: {option_a}")
        print(f"     Option B: {option_b}")
        print(f"     Words: {len(script.split())}")

        return headline, script, option_a, option_b, theme_name

    except ImportError:
        print("  ⚠️ google-genai not installed — using fallback")
        return _get_fallback_script(theme)
    except Exception as e:
        print(f"  ⚠️ Gemini API error: {e} — using fallback")
        return _get_fallback_script(theme)


def _get_fallback_script(theme):
    """Returns a pre-written fallback script when the API is unavailable."""
    fallback_scripts = [
        {
            "headline": "THIS CHOICE WILL BREAK YOU",
            "script": "Would you rather know the exact date of your death... or the cause? Think about it. If you know the date, every single day becomes a countdown. You'd watch the clock, knowing exactly when it ends. But if you know the cause... you'd spend your entire life avoiding it. Car crash? Never drive again. Heart attack? Obsess over every heartbeat. Either way, you lose your peace. But at least one gives you a chance to fight it. Comment A or B right now. I need to know.",
            "option_a": "Know the date",
            "option_b": "Know the cause",
        },
        {
            "headline": "WOULD YOU RATHER READ MINDS",
            "script": "Would you rather read everyone's thoughts... or be invisible whenever you want? Sounds amazing, right? But imagine hearing what your best friend REALLY thinks about you. Every insecurity, every judgment, playing on repeat in your head. Now invisibility... you could go anywhere, do anything, no consequences. But here's the catch... you'd realize how little people talk about you when you're not around. Both options destroy your peace. Type 1 for mind reading or 2 for invisibility.",
            "option_a": "Read minds",
            "option_b": "Be invisible",
        },
        {
            "headline": "10 MILLION OR START OVER",
            "script": "Would you rather get 10 million dollars right now... or go back to age 10 with everything you know today? The money sounds obvious. But think about it. You'd still be the same person, just richer. Now imagine going back to 10. You'd ace every test, avoid every mistake, invest in Bitcoin at one dollar. You'd basically be a genius kid. But you'd also lose every relationship you've built since then. Your best friend? Gone. Your partner? They don't know you yet. Comment A or B. This one splits everyone.",
            "option_a": "10 million now",
            "option_b": "Restart at age 10",
        },
        {
            "headline": "NEVER LIE OR NEVER BE LIED TO",
            "script": "Would you rather never be able to lie again... or never be lied to? If you can't lie, every awkward question gets a brutally honest answer. Your boss asks if you like the job? Your partner asks if they look good? No filter. Ever. But if nobody can lie TO you... you'd find out how much of your life is built on comfortable lies. Your friends, your family, even yourself. The truth isn't always kind. One protects others. One protects you. Type 1 or 2. No middle ground.",
            "option_a": "Never lie again",
            "option_b": "Never be lied to",
        },
        {
            "headline": "FLY SLOW OR RUN FAST",
            "script": "Would you rather fly... but only at walking speed, or run at 200 miles per hour but never fly? Flying sounds like the dream. But imagine floating through the sky at 3 miles per hour. Birds would pass you. Planes would laugh. You'd look ridiculous. Now running at 200mph... you'd be the fastest human alive. Cross the country in hours. But you could never leave the ground. Never feel weightless. Never touch the clouds. One is freedom. The other is power. Comment which one you'd pick.",
            "option_a": "Fly slowly",
            "option_b": "Run at 200mph",
        },
    ]

    chosen = random.choice(fallback_scripts)
    return chosen["headline"], chosen["script"], chosen["option_a"], chosen["option_b"], theme["theme"]


if __name__ == "__main__":
    # Test with a random theme
    headline, script, opt_a, opt_b, theme_name = generate_wyr_script()
    print(f"\n--- RESULT ---")
    print(f"THEME: {theme_name}")
    print(f"HEADLINE: {headline}")
    print(f"OPTION A: {opt_a}")
    print(f"OPTION B: {opt_b}")
    print(f"SCRIPT: {script}")
    print(f"WORDS: {len(script.split())}")
