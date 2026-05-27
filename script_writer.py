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
3. ESCALATION (3-4 sentences): Build tension fast. Show the conflict. Make the viewer feel the unfairness, audacity, or stupidity.
4. PART 1 CLIFFHANGER (If story is long): If the story requires a Part 2, end Part 1 abruptly at peak tension and say: "Part 2 is on my profile."
5. COMMENT BAIT ENDING (For the final part): The LAST sentence of the final part must be an open question that forces the viewer to comment. Rotate between styles like: "Was I right? Tell me below.", "Comment KARMA if they deserved it.", "Rate this 1 to 10.", "Would YOU have done the same?", "Who was the real problem here?" No resolution.

CRITICAL RULES FOR AUTHENTICITY:
1. NO AI CLICHÉS: Never use "You won't believe", "Little did I know", "Plot twist!", "Fast forward to", "Let's just say", "brace yourself", "here's where it gets interesting".
2. MATCH THE VIBE (CRITICAL): Adapt your tone to the story. If it's petty revenge, sound angry and petty. If it's a TIFU, sound embarrassed and conversational. Use raw language ("honestly," "literally," "so basically").
3. USE PAUSES: You MUST use punctuation like ellipses (...) and commas (,) to naturally add pauses and emotion to the narration. The AI voiceover needs these to not sound monotonic!
4. WRITE LIKE A PERSON TALKING: Use contractions ("I'm", "didn't", "she's"). Use natural filler phrases sparingly.
5. PROPER APOSTROPHES: Always write "I'm" not "im", "don't" not "dont". The TTS voice will butcher missing apostrophes.
6. SHORT SENTENCES: Maximum 15 words per sentence for punchy delivery. Mix short and medium sentences.
7. LENGTH: 130-150 words EXACTLY. Long enough to set up the story properly, short enough for 60 seconds.
8. CLARITY FIRST: If the Reddit story is confusing or long, distill it into something anyone can follow in 60 seconds.
9. AUDIO ONLY: No brackets, no stage directions, no emojis, no markdown."""

USER_PROMPT_TEMPLATE = """Transform this Reddit story into a viral YouTube Shorts script.

The viewer has NO context. The first word of the script must be a shock word or action verb — NOT "I", "My", or "So". End the final script with an open question to bait comments (rotate styles: "Was I wrong?", "Comment KARMA if they deserved it.", "Rate this 1-10.", etc.). If the story is long, split it into two parts.

Respond ONLY with a valid JSON object in this exact format:
{{
  "headline": "A punchy ALL CAPS confession-style title (5-9 words). Examples: 'I REPORTED MY OWN BOSS TO HR', 'SHE SOLD MY CAR WHILE I WAS ASLEEP'",
  "script": "Part 1 (100-115 words). Starts dramatic. Builds tension. If there is a Part 2, end abruptly with 'Part 2 is on my profile.' If no Part 2, end with the comment-bait question.",
  "script_part2": "(Optional) Part 2 (100-115 words). ONLY include if the original story is too long to fit in 115 words. Starts with a 1-sentence recap. Ends with the comment-bait question."
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
        
        # Validate — target is 100-115 words for a ~45s Short
        word_count = len(script.split())
        if word_count > 125:
            # Trim to ~115 words at a sentence boundary
            words = script.split()
            trimmed = ' '.join(words[:115])

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
