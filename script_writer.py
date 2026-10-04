"""
AI Script Writer — Transforms raw Reddit stories into viral narration scripts.

Uses Google Gemini 2.5 Flash (free tier: 15 RPM, 1500 RPD) to:
1. Create a punchy, news-headline-style title
2. Rewrite the story for maximum retention
3. Keep it under 115 words for 45-second Shorts (tight = high completion rate)

Requires: GEMINI_API_KEY environment variable
Fallback: Returns original text if API is unavailable
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

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# The prompt that transforms flat Reddit text into viral gold
SYSTEM_PROMPT = """You are the #1 viral YouTube Shorts scriptwriter. Your scripts have hit 50M+ views. You specialize in Reddit narration — turning raw stories into 45-second scroll-stoppers.

YOUR ONLY GOAL: The viewer must feel something INSTANTLY and be unable to stop watching.

THE PERFECT SCRIPT STRUCTURE:
1. HOOK — CRITICAL: The FIRST WORD must be a dramatic verb, object, or name. NEVER "I", "My", "So", "Today", "This", "There", or "When". NO EXCEPTIONS.
   Examples of GOOD first words: "She", "Karen", "The text", "My boss", "He", "They", "Her scream", "Blood", "Everything"
   Examples of GOOD hooks: "She sold my car while I was sleeping.", "Karen fired me by accident.", "The text destroyed my marriage.", "My boss called me at 3 AM."
   Examples of BAD hooks (NEVER DO THIS): "I sent a text", "My life changed", "So this happened", "Today I discovered"
   The hook must drop directly into the most dramatic moment in 1 sentence ONLY.
2. SETUP (2-3 sentences): Briefly explain who the people are and what happened. The viewer knows NOTHING. Be crystal clear. Use names or clear roles ("my landlord", "my sister's boyfriend").
3. ESCALATION (2-3 sentences): Build tension fast. Show the conflict. Make the viewer feel the unfairness, audacity, or stupidity.
4. PART 1 CLIFFHANGER (If story is long): If the story requires a Part 2, end Part 1 abruptly at peak tension and say: "Part 2 is on my profile."
5. ENGAGEMENT CTA (For the final part): The LAST sentence of the final part must explicitly ask an open question AND ask them to subscribe. Rotate between styles like: "Was I right? Tell me below and subscribe.", "Comment KARMA if they deserved it, and hit subscribe.", "Who was the real problem here? Let me know and subscribe for more."

CRITICAL RULES FOR AUTHENTICITY:
1. NO AI CLICHÉS: Never use "You won't believe", "Little did I know", "Plot twist!", "Fast forward to", "Let's just say", "brace yourself", "here's where it gets interesting".
2. MATCH THE VIBE (CRITICAL): Adapt your tone to the story. If it's petty revenge, sound angry and petty. If it's a TIFU, sound embarrassed and conversational. Use raw language ("honestly," "literally," "so basically").
3. USE PAUSES: You MUST use punctuation like ellipses (...) and commas (,) to naturally add pauses and emotion to the narration. The AI voiceover needs these to not sound monotonic!
4. WRITE LIKE A PERSON TALKING: Use contractions ("I'm", "didn't", "she's"). Use natural filler phrases sparingly.
5. PROPER APOSTROPHES: Always write "I'm" not "im", "don't" not "dont". The TTS voice will butcher missing apostrophes.
6. SHORT SENTENCES: Maximum 15 words per sentence for punchy delivery. Mix short and medium sentences.
7. LENGTH: 80-100 words EXACTLY. Shorts under 45 seconds get 3x higher completion rate. Be ruthlessly concise.
8. CLARITY FIRST: If the Reddit story is confusing or long, distill it into something anyone can follow in 60 seconds.
9. AUDIO ONLY: No brackets, no stage directions, no emojis, no markdown."""

USER_PROMPT_TEMPLATE = """Transform this Reddit story into a viral YouTube Shorts script.

The viewer has NO context. The first word of the script must be a shock word or action verb — NOT "I", "My", or "So". End the final script with an engagement CTA (rotate styles: "Was I wrong? Let me know and hit subscribe.", "Comment KARMA if they deserved it and subscribe for more.", etc.). If the story is long, split it into two parts.

Respond ONLY with a valid JSON object in this exact format:
{{
  "headline": "A punchy ALL CAPS confession-style title (5-9 words). Examples: 'I REPORTED MY OWN BOSS TO HR', 'SHE SOLD MY CAR WHILE I WAS ASLEEP'",
  "script": "Part 1 (80-100 words). Starts dramatic. Builds tension. If there is a Part 2, end abruptly with 'Part 2 is on my profile.' If no Part 2, end with the engagement CTA.",
  "script_part2": "(Optional) Part 2 (80-100 words). ONLY include if the original story is too long to fit in 100 words. Starts with a 1-sentence recap. Ends with the engagement CTA."
}}

Original Reddit title: {title}

Original Reddit story:
{body}"""


# Viral hook patterns — used to validate and fix weak AI-generated hooks
BANNED_FIRST_WORDS = ["i", "my", "so", "today", "this", "there", "when", "once", "recently", "yesterday"]
STRONG_HOOK_WORDS = ["betrayed", "fired", "caught", "destroyed", "exposed", "ruined", "sold", "stole",
                     "screamed", "demanded", "called", "texted", "sued", "reported", "banned", "blocked"]


def validate_and_fix_hook(script):
    """
    Validates that the script starts with a strong hook.
    If the first word is weak (I, My, So, etc.), attempts to restructure it.

    Returns: (fixed_script, is_valid)
    """
    if not script:
        return script, False

    first_word = script.split()[0].lower().strip('.,!?"\'')

    # Check if it starts with a banned word
    if first_word in BANNED_FIRST_WORDS:
        print(f"  ⚠️ Weak hook detected: starts with '{first_word}'")

        # Attempt programmatic fix
        words = script.split()

        # Pattern: "My [noun] [verb]..." -> "[Noun] [verb]..."
        if first_word == "my" and len(words) > 2:
            fixed_script = ' '.join(words[1:])  # Remove "My"
            fixed_script = fixed_script[0].upper() + fixed_script[1:]  # Capitalize first letter
            print(f"  🔧 Fixed hook: '{first_word} {words[1]}...' -> '{fixed_script.split()[0]}...'")
            return fixed_script, True

        # Pattern: "I [verb]..." -> "[Verb]..." (only if verb is dramatic)
        if first_word == "i" and len(words) > 1:
            second_word = words[1].lower().strip('.,!?"\'')
            if second_word in STRONG_HOOK_WORDS or second_word in ['accidentally', 'just', 'sent', 'saw']:
                # Remove "I" and capitalize the verb
                fixed_script = ' '.join(words[1:])
                fixed_script = fixed_script[0].upper() + fixed_script[1:]
                print(f"  🔧 Fixed hook: 'I {words[1]}...' -> '{fixed_script.split()[0]}...'")
                return fixed_script, True

        # Pattern: "So..." or "Today..." -> just remove it
        if first_word in ["so", "today", "recently", "yesterday"]:
            fixed_script = ' '.join(words[1:])
            if fixed_script:
                fixed_script = fixed_script[0].upper() + fixed_script[1:]
                print(f"  🔧 Fixed hook: removed filler word '{first_word}'")
                return fixed_script, True

        return script, False

    # First sentence should be under 15 words for maximum impact
    first_sentence = script.split('.')[0] if '.' in script else script.split('!')[0] if '!' in script else script
    word_count = len(first_sentence.split())

    if word_count > 15:
        print(f"  ⚠️ Hook too long: {word_count} words (should be < 15)")
        return script, False

    return script, True


    if word_count > 15:
        print(f"  ⚠️ Hook too long: {word_count} words (should be < 12)")
        return script, False

    return script, True


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
            headline = data.get("headline", title).strip()
            script = data.get("script", "").strip()
            script_part2 = data.get("script_part2", "")
            if script_part2:
                script_part2 = script_part2.strip()
            
            if not script:
                print("  ⚠️ AI generated an empty script! Falling back to raw text.")
                return title, body, None
        except json.JSONDecodeError as e:
            print(f"  ⚠️ Failed to parse JSON: {e}, falling back to raw text")
            print(f"  Raw response was: {result_text}")
            return title, body, None
        
        # Remove any markdown formatting
        headline = re.sub(r'[*#_]', '', headline).strip('"').strip("'")
        script = re.sub(r'[*#_]', '', script)

        # Validate hook strength
        script, hook_valid = validate_and_fix_hook(script)
        if not hook_valid:
            print(f"  ⚠️ Hook validation failed — script may have weak opening")

        # Validate — target is 80-100 words for a ~30-40s Short
        word_count = len(script.split())
        if word_count > 105:
            # Trim to ~90 words at a sentence boundary
            words = script.split()
            trimmed = ' '.join(words[:90])

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
