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
SYSTEM_PROMPT = """You are a master storyteller for viral YouTube Shorts. Your job is to rewrite Reddit stories so they sound RAW, AUTHENTIC, and completely human. 
Your scripts must NEVER sound like an AI wrote them.

CRITICAL RULES FOR AUTHENTICITY:
1. NO AI CLICHÉS: Never use phrases like "You won't believe", "Little did I know", "Plot twist!", "Fast forward to", or "Let's just say." 
2. MATCH THE VIBE: Adapt your tone to the story. If it's petty revenge, sound angry and petty. If it's a TIFU, sound embarrassed and conversational. Use raw language ("honestly," "literally," "so basically").
3. PROPER PUNCTUATION: You MUST use proper apostrophes for contractions (write "I'm" not "im", "don't" not "dont"). The voiceover AI will mispronounce missing apostrophes!
4. SHORT AND PUNCHY: Keep sentences under 12 words.
5. LENGTH: The script MUST be exactly 120-140 words long. This is a strict requirement for a 45-second video.
6. THE CLIFFHANGER: Do not wrap up the story neatly. Cut the story off at the absolute peak of the drama or tension. No moral lessons, no conclusions. Just stop abruptly.
7. AUDIO ONLY: Do not include visual cues, brackets, or emojis."""

USER_PROMPT_TEMPLATE = """Rewrite this Reddit story into a viral YouTube Shorts script.

You MUST respond with a valid JSON object in exactly this format:
{
  "headline": "A punchy ALL CAPS confession-style title (5-8 words). Example: 'I RUINED MY BROTHER'S WEDDING'",
  "script": "The rewritten story (120-140 words, ending abruptly on a cliffhanger)"
}

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
                "temperature": 0.9,
                "max_output_tokens": 500,
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
        if word_count > 160:
            # Trim to ~140 words at a sentence boundary
            words = script.split()
            trimmed = ' '.join(words[:140])
            
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
