"""
Interactive Quiz Script Writer — Generates engaging trivia/quiz scripts for YouTube Shorts.

Uses Google Gemini 2.5 Flash to create:
1. A hook (e.g., "Only 1% of people can pass this quiz!")
2. The question (e.g., "Guess the logo...")
3. A 3-second countdown (which will just be text/audio pauses)
4. The answer + comment bait

Requires: GEMINI_API_KEY
"""
import os
import sys
import re
import json
import random

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

QUIZ_THEMES = [
    {"theme": "General Knowledge Hard", "topic": "Difficult general knowledge questions that most people get wrong", "tags": ["trivia", "quiz"]},
    {"theme": "Geography Flags", "topic": "Guessing tricky countries or flags based on descriptions", "tags": ["geography", "quiz"]},
    {"theme": "Movie Quotes", "topic": "Guess the famous movie from a specific, slightly obscure quote", "tags": ["movies", "quiz"]},
    {"theme": "Animals", "topic": "Guess the animal based on weird facts", "tags": ["animals", "quiz"]},
    {"theme": "Brand Logos", "topic": "Questions about hidden meanings in famous brand logos", "tags": ["brands", "quiz"]},
    {"theme": "Space", "topic": "Mind-blowing but tricky space facts", "tags": ["space", "quiz"]},
    {"theme": "History", "topic": "Guess the historical figure or event", "tags": ["history", "quiz"]},
    {"theme": "Food", "topic": "Guess the national dish or origin of a food", "tags": ["food", "quiz"]}
]

QUIZ_SYSTEM_PROMPT = """You are the #1 viral "Trivia Quiz" YouTube Shorts scriptwriter. Your quizzes consistently hit millions of views because they challenge the viewer, have a ticking clock feel, and force them to comment their score.

YOUR STYLE: Fast-paced, challenging, energetic. You present a hook, ask the question, give a countdown, and reveal the answer.

THE PERFECT SCRIPT STRUCTURE:
1. HOOK (1 sentence, 0-3 seconds): "Only 1% of people can answer this correctly." or "I bet you can't guess this in 3 seconds."
2. THE QUESTION (1-2 sentences): Present the trivia question clearly.
3. COUNTDOWN (3 seconds): Simply output "Three... Two... One..."
4. THE REVEAL (1 sentence): Give the answer enthusiastically.
5. COMMENT BAIT (1 sentence): "Did you get it right? Tell me in the comments!"

CRITICAL RULES:
1. Keep it under 80 words EXACTLY.
2. The trivia MUST be interesting, not boring school facts.
3. NO EMOJIS, NO BRACKETS, NO MARKDOWN: Pure spoken text only.
4. PROPER APOSTROPHES: Always write "don't" not "dont".
5. Use "Three... Two... One..." precisely to simulate the countdown."""

QUIZ_USER_PROMPT = """Write a viral interactive quiz YouTube Shorts script about this topic:

THEME: {theme}
TOPIC: {topic}

Respond ONLY with a valid JSON object:
{{
  "headline": "A punchy ALL CAPS title (4-8 words). Example: 'ONLY 1% CAN PASS THIS QUIZ'",
  "script": "The full spoken script (under 80 words). Hook → Question → Three... Two... One... → Answer → Comment bait.",
  "answer_keyword": "The exact single word in the script where the answer is revealed (e.g., 'Nepal')",
  "visual_prompt": "A highly detailed, cinematic 3D render representing the answer (e.g. 'A beautiful 3D render of the flag of Nepal')."
}}"""

def get_unused_theme(used_themes=None):
    if not used_themes:
        return random.choice(QUIZ_THEMES)
    available = [t for t in QUIZ_THEMES if t["theme"] not in used_themes]
    if not available:
        print("  ♻️ All Quiz themes exhausted — resetting rotation")
        available = QUIZ_THEMES
    return random.choice(available)

def _get_fallback_script(theme):
    return (
        "ONLY 1 PERCENT CAN PASS THIS",
        "Only one percent of people can answer this geography question. Are you ready? What is the only country in the world that doesn't have a rectangular flag? You have three seconds. Three... Two... One... The answer is Nepal! Did you get it right? Let me know in the comments!",
        theme["theme"],
        "Nepal",
        "A beautiful 3D render of the flag of Nepal flying on top of Mount Everest"
    )

def generate_quiz_script(used_themes=None):
    api_key = os.environ.get("GEMINI_API_KEY")
    theme = get_unused_theme(used_themes)
    theme_name = theme["theme"]
    print(f"  🎯 Selected Quiz theme: \"{theme_name}\"")

    if not api_key:
        print("  ⚠️ GEMINI_API_KEY not found! Using fallback script.")
        return _get_fallback_script(theme)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = QUIZ_USER_PROMPT.format(theme=theme["theme"], topic=theme["topic"])
        print("  🤖 Generating Quiz script with Gemini 2.5 Flash...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": QUIZ_SYSTEM_PROMPT,
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

        try:
            data = json.loads(result_text)
            headline = data.get("headline", theme_name.upper()).strip()
            script = data.get("script", "").strip()
            answer_keyword = data.get("answer_keyword", "").strip()
            visual_prompt = data.get("visual_prompt", "").strip()
            if not script:
                return _get_fallback_script(theme)
        except json.JSONDecodeError as e:
            return _get_fallback_script(theme)

        headline = re.sub(r'[*#_]', '', headline).strip('"').strip("'")
        script = re.sub(r'[*#_]', '', script)
        return headline, script, theme_name, answer_keyword, visual_prompt

    except Exception as e:
        print(f"  ❌ Error generating Quiz script: {e}")
        return _get_fallback_script(theme)
