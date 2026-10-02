import os
import sys
import re
import json

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PROMPTS = {
    "two_truths": {
        "title": "Two Truths and a Lie",
        "desc": "Two crazy but true facts and one very believable lie about a specific topic."
    },
    "riddle": {
        "title": "Riddle of the Day",
        "desc": "A clever and challenging riddle that requires lateral thinking."
    },
    "survive": {
        "title": "Would You Survive?",
        "desc": "A dangerous wilderness or historical survival scenario with 3 choices."
    },
    "spot_fake": {
        "title": "Spot the Fake",
        "desc": "Describe a scenario where the user has to identify which of two things is a fake or myth."
    }
}

SYSTEM_PROMPT = """You are the #1 viral "Interactive Challenge" YouTube Shorts scriptwriter. Your videos consistently hit millions of views because they challenge the viewer, have a ticking clock feel, and force them to comment their guess.

YOUR STYLE: Fast-paced, challenging, energetic. You present a hook, ask the question/challenge, give a countdown, and reveal the answer.

THE PERFECT SCRIPT STRUCTURE:
1. HOOK (1 sentence, 0-3 seconds): Grab attention immediately based on the format.
2. THE CHALLENGE (1-2 sentences): Present the riddle, the survival choices, or the two truths and a lie.
3. COUNTDOWN (3 seconds): Simply output "Three... Two... One..."
4. THE REVEAL (1 sentence): Give the answer enthusiastically.
5. COMMENT BAIT (1 sentence): "Did you get it right? Tell me in the comments!"

CRITICAL RULES:
1. Keep it under 80 words EXACTLY.
2. NO EMOJIS, NO BRACKETS, NO MARKDOWN: Pure spoken text only.
3. Use "Three... Two... One..." precisely to simulate the countdown.
4. Provide a highly detailed `visual_prompt` for the exact moment the answer is revealed. This prompt will be sent to an AI Image Generator. Make it cinematic and beautiful."""

USER_PROMPT = """Write a viral interactive YouTube Shorts script based on this challenge:

FORMAT: {format_title}
DETAILS: {format_desc}

Respond ONLY with a valid JSON object:
{{
  "headline": "A punchy ALL CAPS title (4-8 words). Example: 'TWO TRUTHS AND A LIE'",
  "script": "The full spoken script (under 80 words). Hook → Challenge → Three... Two... One... → Answer → Comment bait.",
  "answer_keyword": "The exact single word in the script where the answer is revealed (e.g., 'Spider')",
  "visual_prompt": "A highly detailed, cinematic 3D render representing the answer (e.g. 'A cinematic 3D render of a giant spider in a web')."
}}"""

def generate_interactive_script(format_type):
    api_key = os.environ.get("GEMINI_API_KEY")
    theme = PROMPTS.get(format_type, PROMPTS["riddle"])
    theme_name = theme["title"]
    print(f"  🎯 Selected Interactive theme: \"{theme_name}\"")

    if not api_key:
        print("  ⚠️ GEMINI_API_KEY not found! Using fallback.")
        return theme_name.upper(), "This is a fallback script. Three... Two... One... Done!", theme_name, "Done", "A cool image"

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = USER_PROMPT.format(format_title=theme_name, format_desc=theme["desc"])
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 1.0,
                "max_output_tokens": 400,
                "response_mime_type": "application/json",
            }
        )
        result_text = response.text.strip()
        if result_text.startswith("```json"): result_text = result_text[7:]
        elif result_text.startswith("```"): result_text = result_text[3:]
        if result_text.endswith("```"): result_text = result_text[:-3]
        result_text = result_text.strip()

        data = json.loads(result_text)
        headline = data.get("headline", theme_name.upper()).strip()
        script = data.get("script", "").strip()
        answer_keyword = data.get("answer_keyword", "").strip()
        visual_prompt = data.get("visual_prompt", "").strip()

        headline = re.sub(r'[*#_]', '', headline).strip('"').strip("'")
        script = re.sub(r'[*#_]', '', script)
        return headline, script, theme_name, answer_keyword, visual_prompt

    except Exception as e:
        print(f"  ❌ Error generating Interactive script: {e}")
        return theme_name.upper(), "This is a fallback script. Three... Two... One... Done!", theme_name, "Done", "A cool image"
