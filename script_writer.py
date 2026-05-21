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
SYSTEM_PROMPT = """You are a viral YouTube Shorts script writer. Your scripts get MILLIONS of views because they're impossible to stop watching.

Your rules:
1. You write scripts that are READ ALOUD by a narrator — no visual directions, no emojis, no hashtags
2. Every script MUST start with a punchy headline (like a news ticker) in ALL CAPS, followed by the story
3. Use short, punchy sentences (under 12 words each)
4. Create suspense — make the viewer NEED to know what happens next
5. Include at least one twist or dramatic reveal
6. End abruptly — no moral, no conclusion, no "and that's my story". Just stop at the most dramatic moment
7. The total script MUST be under 140 words (this is critical — it will be a 45-55 second video)
8. Write in first person as if YOU are telling the story
9. Use conversational language — speak like a real person, not a writer
10. Add dramatic pauses with "..." before reveals"""

USER_PROMPT_TEMPLATE = """Rewrite this Reddit story into a viral YouTube Shorts script.

IMPORTANT FORMAT:
- Line 1: A punchy headline in ALL CAPS (5-8 words, like a news headline). Example: "MY BOSS FIRED ME FOR BEING RIGHT"
- Line 2 onward: The rewritten story (first person, dramatic, suspenseful)
- Total: UNDER 140 words
- End abruptly at the most dramatic moment

Original Reddit title: {title}

Original Reddit story:
{body}

Write the viral script now:"""


def rewrite_story(title, body):
    """
    Uses Gemini 2.5 Flash to rewrite a Reddit story into a viral script.
    
    Returns:
        tuple: (headline, script) — the punchy title and rewritten body
        Falls back to (title, body) if API is unavailable
    """
    if not GEMINI_API_KEY:
        print("  ⚠️ No GEMINI_API_KEY set — using raw Reddit text")
        return title, body
    
    try:
        from google import genai
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = USER_PROMPT_TEMPLATE.format(title=title, body=body)
        
        print("  🤖 Rewriting story with Gemini 2.5 Flash...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.9,  # Creative but not wild
                "max_output_tokens": 400,
            }
        )
        
        result_text = response.text.strip()
        
        if not result_text:
            print("  ⚠️ Empty response from Gemini — using raw text")
            return title, body
        
        # Parse the response: first line = headline, rest = script
        lines = result_text.strip().split('\n')
        
        # Find the headline (first non-empty line, should be ALL CAPS)
        headline = ""
        script_lines = []
        found_headline = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if not found_headline:
                # Remove any markdown formatting
                headline = re.sub(r'[*#_]', '', line).strip()
                # Remove quotes if present
                headline = headline.strip('"').strip("'").strip()
                found_headline = True
            else:
                # Remove any markdown formatting from body too
                clean_line = re.sub(r'[*#_]', '', line).strip()
                if clean_line:
                    script_lines.append(clean_line)
        
        script = ' '.join(script_lines)
        
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
