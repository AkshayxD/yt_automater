"""
AI Script Writer — Transforms raw Reddit stories into viral narration scripts.

Uses Google Gemini 2.5 Flash (free tier: 15 RPM, 1500 RPD) to:
1. Create a punchy, news-headline-style title
2. Rewrite the story for maximum retention
3. Keep it under 140 words for 60-second Shorts

Requires: GEMINI_API_KEY environment variable
Fallback: Returns original text if API is unavailable
"""
import os
import sys
import re

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# The prompt that transforms flat Reddit text into viral gold
SYSTEM_PROMPT = """You are the #1 viral YouTube Shorts scriptwriter. Your scripts have hit 50M+ views. You specialize in Reddit narration — turning raw stories into 45-second scroll-stoppers.

YOUR ONLY GOAL: The viewer must feel something INSTANTLY and be unable to stop watching.

THE PERFECT SCRIPT STRUCTURE:
1. HOOK — first 1 sentence ONLY. Drop directly into the most dramatic moment. The first word must be a shock word or action verb. NEVER start with "I", "My", "So", or "Today". Good openers: "She sold my car while I was sleeping.", "My boss just fired me — by accident.", "The text I sent to the wrong person ended my marriage."
2. SETUP (2-3 sentences): Briefly explain who the people are and what happened. The viewer knows NOTHING. Be crystal clear. Use names or clear roles ("my landlord", "my sister's boyfriend").
3. ESCALATION (4-5 sentences): Build tension fast. Show the conflict. Make the viewer feel the unfairness, audacity, or stupidity.
4. PART 1 CLIFFHANGER (If story is long): If the story requires a Part 2, end Part 1 abruptly at peak tension and say: "Part 2 is on my profile."
5. COMMENT BAIT ENDING (For the final part): The LAST sentence of the final part must be an open question that forces the viewer to comment. Example: "Was I right? Tell me in the comments." or "Comment 'YTA' or 'NTA'." No resolution.

CRITICAL RULES:
1. NO AI CLICHÉS: Never use "You won't believe", "Little did I know", "Plot twist", "Fast forward", "Let's just say", "brace yourself", "here's where it gets interesting", "needless to say".
2. NO SOFT OPENERS: Never start with "I", "My", "So", "Today", "Once", "There was", "Meet". Start with the drama.
3. WRITE LIKE A PERSON: Use contractions (I'm, didn't, she's). Short punchy sentences. Max 12 words per sentence.
4. PROPER APOSTROPHES: Always write "I'm" not "im", "don't" not "dont". TTS butchers missing apostrophes.
5. LENGTH: 110-125 words EXACTLY. Tight and punchy. This is a 45-second Short, not an essay.
6. AUDIO ONLY: No brackets, no stage directions, no emojis, no markdown."""

USER_PROMPT_TEMPLATE = """Transform this Reddit story into a viral YouTube Shorts script.

The viewer has NO context. The first word of the script must be a shock word or action verb — NOT "I", "My", or "So". End the final script with an open question to bait comments (e.g. "Who was wrong?"). If the story is long, split it into two parts.

Respond ONLY with a valid JSON object in this exact format:
{{
  "headline": "A punchy ALL CAPS confession-style title (5-9 words). Examples: 'I REPORTED MY OWN BOSS TO HR', 'SHE SOLD MY CAR WHILE I WAS ASLEEP'",
  "script": "Part 1 (110-125 words). Starts dramatic. Builds tension. If there is a Part 2, end abruptly with 'Part 2 is on my profile.' If no Part 2, end with the comment-bait question.",
  "script_part2": "(Optional) Part 2 (110-125 words). ONLY include if the original story is too long to fit in 125 words. Starts with a 1-sentence recap. Ends with the comment-bait question."
}}

Original Reddit title: {title}

Original Reddit story:
{body}"""


def rewrite_story(title, body):
    """
    Uses Gemini 2.5 Flash to rewrite a Reddit story into a viral script.
    
    Returns:
        tuple: (headline, script_part1, script_part2) — the punchy title and rewritten body parts (part2 may be None)
        Falls back to (title, body, None) if API is unavailable
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  ⚠️ GEMINI_API_KEY not found! Falling back to raw text.")
        return title, body, None

    try:
        from google import genai
        import json
        client = genai.Client(api_key=api_key)
        
        prompt = USER_PROMPT_TEMPLATE.format(title=title, body=body)
        
        print("  🤖 Rewriting story with Gemini 2.5 Flash...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 1.0,   # Higher creativity — less bland, more punchy
                "max_output_tokens": 600,
                "response_mime_type": "application/json",
            }
        )
        
        result_text = response.text.strip()
        
        try:
            data = json.loads(result_text)
            headline = data.get("headline", title).strip()
            script = data.get("script", "").strip()
            script_part2 = data.get("script_part2", "")
            if script_part2:
                script_part2 = script_part2.strip()
            
            if not script:
                print("  ⚠️ AI generated an empty script! Falling back to raw text.")
                return title, body, None
        except json.JSONDecodeError:
            print("  ⚠️ Failed to parse JSON, falling back to raw text")
            return title, body, None
        
        # Remove any markdown formatting
        headline = re.sub(r'[*#_]', '', headline).strip('"').strip("'")
        script = re.sub(r'[*#_]', '', script)
        
        # Validate — target is 110-125 words for a ~45s Short
        word_count = len(script.split())
        if word_count > 140:
            # Trim to ~120 words at a sentence boundary
            words = script.split()
            trimmed = ' '.join(words[:125])

            # Find the last sentence boundary (. ! or ?)
            boundaries = [trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?')]
            last_boundary = max(boundaries)

            # Only trim if the boundary is in the last 30% of the trimmed string
            if last_boundary > int(len(trimmed) * 0.7):
                script = trimmed[:last_boundary + 1]
            else:
                script = trimmed
            print(f"  ⚠️ Script was {word_count} words — trimmed to {len(script.split())}")        
        print(f"  ✅ AI script generated! Headline: \"{headline}\"")
        print(f"     Script 1: {len(script.split())} words")
        if script_part2:
            print(f"     Script 2: {len(script_part2.split())} words")
        
        return headline, script, script_part2
        
    except ImportError:
        print("  ⚠️ google-genai not installed — using raw text")
        print("     Install with: pip install google-genai")
        return title, body, None
    except Exception as e:
        print(f"  ⚠️ Gemini API error: {e} — using raw text")
        return title, body, None


if __name__ == "__main__":
    # Test with a sample story
    test_title = "TIFU by accidentally sending my boss a text meant for my wife"
    test_body = (
        "So I was texting my wife about how annoying my boss is. "
        "I wrote this long message about how he micromanages everything "
        "and how I wish he would just trust us to do our jobs. "
        "I even said some pretty harsh things about his management style. "
        "Then I hit send. And realized I had sent it to my boss. "
        "Not my wife. My actual boss. The one I was complaining about. "
        "He read it immediately. I saw the blue checkmarks appear. "
        "My phone rang 30 seconds later. It was him. "
        "He just said 'Come to my office. Now.' "
        "I thought I was getting fired for sure."
    )
    
    headline, script, script2 = rewrite_story(test_title, test_body)
    print(f"\n--- RESULT ---")
    print(f"HEADLINE: {headline}")
    print(f"SCRIPT 1: {script}")
    if script2:
        print(f"SCRIPT 2: {script2}")
    print(f"WORDS 1: {len(script.split())}")
