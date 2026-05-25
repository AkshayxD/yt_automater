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
SYSTEM_PROMPT = """You are the top viral YouTube Shorts scriptwriter. You have written scripts that got 50M+ views. Your specialty is Reddit storytelling — turning raw, confusing Reddit posts into perfectly clear, emotionally gripping 60-second narrations.

YOUR #1 GOAL: Make the viewer immediately understand the situation AND feel something (anger, shock, curiosity, secondhand embarrassment). If they don't understand what's happening, they scroll. If they don't feel something, they scroll.

THE PERFECT SCRIPT STRUCTURE:
1. HOOK (first 1-2 sentences): Open with the most shocking, embarrassing, or curiosity-inducing moment. Start IN the drama. Use questions or statements that create a "wait, what?" reaction. Example: "My boss just texted me to come to his office. I had no idea he'd just read the message I sent him by mistake."
2. SETUP (3-5 sentences): Quickly and CLEARLY explain who the people are and what the situation is. The viewer hasn't read the Reddit post — they know NOTHING. Make it crystal clear without being boring. Use real names if available (or generic ones like "my roommate", "my sister"), not just "they".
3. ESCALATION (4-6 sentences): Build the tension. Show the conflict developing. Make the viewer feel the unfairness, the audacity, or the stupidity of the situation.
4. CLIFFHANGER: Cut off at the peak of drama. No resolution. No moral. Just "and then..."

CRITICAL RULES FOR AUTHENTICITY:
1. NO AI CLICH\u00c9S: Never use "You won't believe", "Little did I know", "Plot twist!", "Fast forward to", "Let's just say", "brace yourself", "here's where it gets interesting".
2. WRITE LIKE A PERSON TALKING: Use contractions ("I'm", "didn't", "she's"). Use natural filler phrases sparingly: "honestly", "so basically", "and then", "the thing is".
3. PROPER APOSTROPHES: Always write "I'm" not "im", "don't" not "dont". The TTS voice will butcher missing apostrophes.
4. SHORT SENTENCES: Maximum 15 words per sentence for punchy delivery. Mix short and medium sentences.
5. LENGTH: 130-150 words EXACTLY. Long enough to set up the story properly, short enough for 60 seconds.
6. CLARITY FIRST: If the Reddit story is confusing or long, your job is to distill it into something anyone can follow in 60 seconds.
7. AUDIO ONLY: No brackets, no stage directions, no emojis, no markdown."""

USER_PROMPT_TEMPLATE = """Transform this Reddit story into a viral YouTube Shorts script.

The viewer has NO context — they haven't read the post. Make sure they understand who everyone is, what the situation is, and why it matters. The first sentence must hook them immediately.

Respond ONLY with a valid JSON object in this exact format:
{{
  "headline": "A punchy ALL CAPS confession-style title (5-9 words). Must feel like a tabloid headline or a shocked reaction. Examples: 'I REPORTED MY OWN BOSS TO HR', 'MY ROOMMATE SOLD MY STUFF WHILE I SLEPT'",
  "script": "The rewritten story (130-150 words). Opens with the hook, clearly sets up the situation, builds tension, ends on a cliffhanger."
}}

Original Reddit title: {title}

Original Reddit story:
{body}"""


def rewrite_story(title, body):
    """
    Uses Gemini 2.5 Flash to rewrite a Reddit story into a viral script.
    
    Returns:
        tuple: (headline, script) — the punchy title and rewritten body
        Falls back to (title, body) if API is unavailable
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  ⚠️ GEMINI_API_KEY not found! Falling back to raw text.")
        return title, body

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
            
            if not script:
                print("  ⚠️ AI generated an empty script! Falling back to raw text.")
                return title, body
        except json.JSONDecodeError:
            print("  ⚠️ Failed to parse JSON, falling back to raw text")
            return title, body
        
        # Remove any markdown formatting
        headline = re.sub(r'[*#_]', '', headline).strip('"').strip("'")
        script = re.sub(r'[*#_]', '', script)
        
        # Validate
        word_count = len(script.split())
        if word_count > 170:
            # Trim to ~150 words at a sentence boundary
            words = script.split()
            trimmed = ' '.join(words[:150])
            
            # Find the last sentence boundary (. ! or ?)
            boundaries = [trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?')]
            last_boundary = max(boundaries)
            
            # Only trim if the boundary is in the last 30% of the trimmed string
            # to prevent cutting off the entire story due to early punctuation
            if last_boundary > int(len(trimmed) * 0.7):
                script = trimmed[:last_boundary + 1]
            else:
                script = trimmed
            print(f"  ⚠️ Script was {word_count} words — trimmed to {len(script.split())}")        
        print(f"  ✅ AI script generated! Headline: \"{headline}\"")
        print(f"     Script: {len(script.split())} words")
        
        return headline, script
        
    except ImportError:
        print("  ⚠️ google-genai not installed — using raw text")
        print("     Install with: pip install google-genai")
        return title, body
    except Exception as e:
        print(f"  ⚠️ Gemini API error: {e} — using raw text")
        return title, body


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
    
    headline, script = rewrite_story(test_title, test_body)
    print(f"\n--- RESULT ---")
    print(f"HEADLINE: {headline}")
    print(f"SCRIPT: {script}")
    print(f"WORDS: {len(script.split())}")
