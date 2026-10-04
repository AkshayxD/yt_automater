"""
Number Facts Writer — Generates mind-blowing math, statistics, and scale facts.

Uses Google Gemini 2.5 Flash to create short, viral-worthy number facts that
demonstrate incomprehensible scales, probability, or mathematical phenomena.

Target: 50-70 words for 15-25 second Shorts (highest completion rate format).
"""
import os
import sys
import json
import random

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 30 rotating themes to prevent repetition
FACT_THEMES = [
    "incomprehensible numbers",
    "scale comparison (atoms vs universe)",
    "probability impossibilities",
    "time scales (seconds to billions of years)",
    "speed and distance",
    "wealth comparison",
    "population statistics",
    "brain capacity vs computers",
    "card shuffle probability",
    "pi and infinite decimals",
    "prime number patterns",
    "geometric growth (grains of rice on chessboard)",
    "quantum mechanics scale",
    "light year distances",
    "molecular counts in everyday objects",
    "odds of winning lottery vs struck by lightning",
    "internet data generated per second",
    "historical time compression",
    "factorial explosion (52!)",
    "Planck length vs observable universe",
]

SYSTEM_PROMPT = """You are a viral Shorts scriptwriter specializing in mind-blowing number facts.

Your goal: Make the viewer's brain short-circuit from incomprehensible scale.

STRUCTURE:
1. HOOK (1 sentence): Drop the shocking number or comparison immediately.
   Example: "There are more possible chess games than atoms in the universe."
2. REVEAL (2-3 sentences): Explain the numbers in simple terms. Use comparisons humans can barely grasp.
   Example: "10 to the power of 120 possible games. The universe only has 10 to the 80 atoms. Your brain can't even comprehend this gap."
3. CLOSER (1 sentence): Emphasize the impossibility or mind-blow.
   Example: "Every chess game is cosmically unique."

RULES:
1. Start with the NUMBER or COMPARISON — NEVER "Did you know", "Imagine this", "Here's a fact"
2. Use EXACT numbers when possible (not "millions" — say "8.7 million")
3. 50-70 words EXACTLY (15-25 second runtime)
4. Write like you're telling a friend something unbelievable
5. Use comparisons to things humans understand (atoms, seconds, Earth, grains of sand)
6. Short sentences. Maximum 12 words per sentence.
7. NO emojis, NO brackets, NO markdown
8. Make it VISCERAL — the viewer should feel small or amazed

AVOID:
- Boring facts ("the sun is big")
- Overused facts (library of Babel, monkeys typing Shakespeare)
- Political or controversial numbers"""

USER_PROMPT_TEMPLATE = """Generate a mind-blowing number fact about: {theme}

Respond ONLY with valid JSON:
{{
  "headline": "Punchy ALL CAPS title (5-8 words). Example: 'YOUR BRAIN CAN'T COMPREHEND THIS NUMBER'",
  "script": "The 50-70 word script following the HOOK → REVEAL → CLOSER structure. Start with the number/comparison, end with a Subscribe CTA.",
  "key_number": "The main number featured (for visual emphasis, e.g., '10^120' or '52!' or '8 billion')"
}}"""


def generate_number_fact_script(used_themes=None):
    """
    Generates a mind-blowing number fact script via Gemini AI.

    Args:
        used_themes: List of recently used themes to avoid repetition

    Returns:
        tuple: (headline, script, key_number, theme_name)
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  ⚠️ GEMINI_API_KEY not found! Using fallback fact.")
        return generate_fallback_fact()

    # Pick a theme that hasn't been used recently
    available_themes = [t for t in FACT_THEMES if t not in (used_themes or [])]
    if not available_themes:
        available_themes = FACT_THEMES  # Reset if all used

    theme = random.choice(available_themes)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = USER_PROMPT_TEMPLATE.format(theme=theme)

        print(f"  🔢 Generating Number Fact: {theme}")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 1.1,  # Slightly higher for creativity
                "max_output_tokens": 400,
                "response_mime_type": "application/json",
            }
        )

        result_text = response.text.strip()

        # Clean markdown blocks
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        elif result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        data = json.loads(result_text)
        headline = data.get("headline", "MIND-BLOWING NUMBER FACT").strip().strip('"\'')
        script = data.get("script", "").strip()
        key_number = data.get("key_number", "").strip()

        if not script:
            print("  ⚠️ AI generated empty script — using fallback")
            return generate_fallback_fact()

        # Validate length
        word_count = len(script.split())
        if word_count > 80:
            words = script.split()
            script = ' '.join(words[:70])
            # Trim to sentence boundary
            for punct in ['.', '!', '?']:
                last_idx = script.rfind(punct)
                if last_idx > len(script) * 0.7:
                    script = script[:last_idx + 1]
                    break
            print(f"  ⚠️ Script trimmed from {word_count} to {len(script.split())} words")

        print(f"  ✅ Number Fact generated!")
        print(f"     Theme: {theme}")
        print(f"     Key number: {key_number}")
        print(f"     Words: {len(script.split())}")

        return headline, script, key_number, theme

    except Exception as e:
        print(f"  ⚠️ Gemini API error: {e} — using fallback")
        return generate_fallback_fact()


def generate_fallback_fact():
    """Fallback facts if Gemini API fails."""
    fallbacks = [
        (
            "SHUFFLING CARDS CREATES COSMIC HISTORY",
            "A deck of cards has 52 factorial possible orders. That's 8 followed by 67 zeros. More than atoms in the Milky Way galaxy. Every time you shuffle a deck, you create an order that has never existed in human history. And never will again.",
            "52!",
            "card shuffle probability"
        ),
        (
            "YOUR BRAIN VS THE UNIVERSE",
            "There are more possible chess games than atoms in the observable universe. 10 to the power of 120 versus 10 to the 80. The gap between these numbers is bigger than the gap between 1 and a trillion. Every chess match is cosmically unique.",
            "10^120",
            "scale comparison"
        ),
    ]
    return random.choice(fallbacks)


if __name__ == "__main__":
    # Test generation
    headline, script, key_number, theme = generate_number_fact_script()
    print(f"\n--- RESULT ---")
    print(f"THEME: {theme}")
    print(f"HEADLINE: {headline}")
    print(f"KEY NUMBER: {key_number}")
    print(f"SCRIPT: {script}")
    print(f"WORDS: {len(script.split())}")
