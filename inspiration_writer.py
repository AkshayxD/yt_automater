"""
Inspiration Script Writer — Generates Dark Stoic motivational scripts for YouTube Shorts.

Uses Google Gemini 2.5 Flash (free tier: 15 RPM, 1500 RPD) to create:
1. A bold, provocative headline (ALL CAPS, 4-8 words)
2. A Hook → Lesson → Action script structure
3. Historical Stoic philosopher attribution

Content is 100% original — Stoic philosophy is 2000+ years old (public domain).
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

# --- Stoic Theme Bank ---
# 30 rotating themes to prevent repetition across days.
# Each theme has a core principle and 2-3 sub-angles the AI can explore.
STOIC_THEMES = [
    {"theme": "Silence is Power", "principle": "Controlling your tongue is more powerful than any argument.", "philosophers": ["Marcus Aurelius", "Epictetus"]},
    {"theme": "Amor Fati — Love Your Fate", "principle": "Embrace everything that happens to you, good or bad, as necessary.", "philosophers": ["Marcus Aurelius", "Nietzsche"]},
    {"theme": "Memento Mori — Remember Death", "principle": "Meditating on death makes every moment urgent and precious.", "philosophers": ["Marcus Aurelius", "Seneca"]},
    {"theme": "The Obstacle is the Way", "principle": "Every obstacle contains an opportunity for growth and strength.", "philosophers": ["Marcus Aurelius"]},
    {"theme": "Control What You Can", "principle": "Focus only on what is within your control. Release everything else.", "philosophers": ["Epictetus"]},
    {"theme": "The Danger of Being Too Nice", "principle": "Kindness without boundaries invites exploitation.", "philosophers": ["Marcus Aurelius", "Seneca"]},
    {"theme": "Walk Alone If Necessary", "principle": "Solitude builds strength. The crowd follows; the wise man leads.", "philosophers": ["Seneca", "Epictetus"]},
    {"theme": "Discipline Equals Freedom", "principle": "True freedom comes from mastering yourself, not from doing whatever you want.", "philosophers": ["Epictetus", "Marcus Aurelius"]},
    {"theme": "Never Reveal Your Next Move", "principle": "Strategic silence protects your ambitions from sabotage.", "philosophers": ["Marcus Aurelius", "Seneca"]},
    {"theme": "The Art of Not Reacting", "principle": "Your power lies in your ability to remain calm when others expect chaos.", "philosophers": ["Marcus Aurelius", "Epictetus"]},
    {"theme": "Comfort is the Enemy", "principle": "Growth only happens outside your comfort zone. Comfort breeds weakness.", "philosophers": ["Seneca"]},
    {"theme": "Let Them Misunderstand You", "principle": "Seeking validation is a prison. True strength needs no audience.", "philosophers": ["Marcus Aurelius", "Epictetus"]},
    {"theme": "Your Circle Determines Your Future", "principle": "You become the average of the people you spend the most time with.", "philosophers": ["Seneca", "Epictetus"]},
    {"theme": "Pain is a Teacher", "principle": "Suffering reveals character. What breaks you also builds you.", "philosophers": ["Seneca", "Marcus Aurelius"]},
    {"theme": "The Power of Patience", "principle": "The wise man waits. Impulsive action leads to regret.", "philosophers": ["Epictetus", "Seneca"]},
    {"theme": "Stop Explaining Yourself", "principle": "Those who matter don't need an explanation. Those who don't matter won't believe it anyway.", "philosophers": ["Marcus Aurelius"]},
    {"theme": "Detach From Outcomes", "principle": "Do your best work, then release your attachment to the result.", "philosophers": ["Marcus Aurelius", "Epictetus"]},
    {"theme": "The Ego is the Enemy", "principle": "Pride blinds you. Humility reveals the truth.", "philosophers": ["Marcus Aurelius", "Epictetus"]},
    {"theme": "Master Your Emotions", "principle": "An uncontrolled mind is your greatest enemy. A disciplined mind is your greatest ally.", "philosophers": ["Seneca", "Marcus Aurelius"]},
    {"theme": "Actions Over Words", "principle": "Stop talking about what a good person should be. Just be one.", "philosophers": ["Marcus Aurelius"]},
    {"theme": "Indifference to Insults", "principle": "If someone insults you, choose not to be harmed — and you won't be.", "philosophers": ["Epictetus", "Marcus Aurelius"]},
    {"theme": "The Cost of Revenge", "principle": "The best revenge is to not be like your enemy.", "philosophers": ["Marcus Aurelius"]},
    {"theme": "Time is Your Only Asset", "principle": "We waste time as if we have infinite supply. We don't.", "philosophers": ["Seneca"]},
    {"theme": "Be Water — Adapt", "principle": "Rigidity breaks. Flexibility endures. Adapt to every situation.", "philosophers": ["Marcus Aurelius", "Epictetus"]},
    {"theme": "The Strength in Saying No", "principle": "Every yes to something unimportant is a no to something that matters.", "philosophers": ["Seneca", "Epictetus"]},
    {"theme": "Trust the Process", "principle": "The seed does not see the sun. But it keeps growing. So must you.", "philosophers": ["Marcus Aurelius"]},
    {"theme": "Your Anger Punishes You", "principle": "Anger is an acid that does more harm to the vessel that holds it.", "philosophers": ["Seneca", "Marcus Aurelius"]},
    {"theme": "Simplify Your Life", "principle": "Wealth is not having many possessions, but needing few.", "philosophers": ["Epictetus", "Seneca"]},
    {"theme": "Fear is an Illusion", "principle": "We suffer more in imagination than in reality.", "philosophers": ["Seneca"]},
    {"theme": "Become Unshakeable", "principle": "The wise man is not disturbed by anything external. His peace comes from within.", "philosophers": ["Epictetus", "Marcus Aurelius"]},
]

# System prompt optimized for Dark Stoic motivational scripts
INSPIRATION_SYSTEM_PROMPT = """You are the #1 viral "Dark Stoic" YouTube Shorts scriptwriter. Your videos consistently hit 10M+ views. You write 30-40 second philosophical lessons that make viewers stop, think, and share.

YOUR STYLE: Dark, contemplative, powerful. Think "stoic monk speaking truth in a thunderstorm." Your tone is calm authority — never preachy, never soft.

THE PERFECT SCRIPT STRUCTURE:

1. HOOK (1 sentence, 0-3 seconds): A bold, provocative statement that STOPS the scroll. Must feel like a slap of truth. Use commands ("Stop..."), questions ("Why do you..."), or shocking reframes ("The nicest people carry the heaviest scars."). NEVER start with "In the words of..." or "As the Stoics say...". The hook must stand alone as wisdom.

2. LESSON (3-5 sentences, 3-30 seconds): Deliver the core Stoic teaching. Use the philosopher's name ONCE for authority (e.g., "Marcus Aurelius ruled the most powerful empire on Earth — yet he wrote..."). Keep sentences punchy (≤12 words each). Build from the general principle to a specific, relatable modern-day application.

3. ACTION/CTA (1-2 sentences, 30-40 seconds): End with a concrete micro-action the viewer can take TODAY. Then add subtle engagement bait. Rotate between: "Type STRENGTH if you choose yourself today.", "Save this for when you need it.", "Follow for your daily Stoic lesson.", "Comment the emoji that describes your mood."

CRITICAL RULES:
1. 80-100 words EXACTLY. Shorter = higher completion rate. Every word must earn its place.
2. NO AI clichés: Never use "In a world where...", "Let that sink in", "Here's the thing", "It's time to...". 
3. USE PAUSES: Strategic ellipses (...) and commas create natural breathing room for the deep voiceover. Place pauses before revelations.
4. WRITE LIKE SPOKEN WORD: Contractions ("don't", "you'll"), fragments ("Not them. You."), rhetorical questions.
5. NO EMOJIS, NO BRACKETS, NO MARKDOWN: Pure spoken text only.
6. DARK TONE: This is not motivational fluff. This is hard truth delivered with gravitas. Think midnight, rain, stone.
7. PROPER APOSTROPHES: Always write "don't" not "dont", "you're" not "youre"."""

INSPIRATION_USER_PROMPT = """Write a viral Dark Stoic YouTube Shorts script about this theme:

THEME: {theme}
CORE PRINCIPLE: {principle}
REFERENCE PHILOSOPHER(S): {philosophers}

Respond ONLY with a valid JSON object:
{{
  "headline": "A punchy ALL CAPS title (4-8 words). Examples: 'SILENCE IS POWER', 'STOP EXPLAINING YOURSELF', 'THE DANGER OF BEING TOO NICE'",
  "script": "The full spoken script (80-100 words). Hook → Lesson → Action structure. Must reference the philosopher naturally.",
  "philosopher": "The primary philosopher referenced (e.g., 'Marcus Aurelius')"
}}"""


def get_unused_theme(used_themes=None):
    """
    Picks a Stoic theme that hasn't been used recently.
    
    Args:
        used_themes: List of recently used theme names to avoid
    
    Returns:
        dict with 'theme', 'principle', 'philosophers' keys
    """
    if not used_themes:
        return random.choice(STOIC_THEMES)
    
    # Filter out recently used themes
    available = [t for t in STOIC_THEMES if t["theme"] not in used_themes]
    
    if not available:
        # All themes used — reset and pick any
        print("  ♻️ All Stoic themes exhausted — resetting rotation")
        available = STOIC_THEMES
    
    return random.choice(available)


def generate_inspiration_script(used_themes=None):
    """
    Generates a Dark Stoic motivational script using Gemini AI.
    
    Args:
        used_themes: List of recently used theme names to avoid repetition
    
    Returns:
        tuple: (headline, script, philosopher, theme_name)
        Falls back to a pre-written script if API is unavailable
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # Pick a fresh theme
    theme = get_unused_theme(used_themes)
    theme_name = theme["theme"]
    print(f"  🏛️ Selected Stoic theme: \"{theme_name}\"")
    print(f"     Philosopher(s): {', '.join(theme['philosophers'])}")
    
    if not api_key:
        print("  ⚠️ GEMINI_API_KEY not found! Using fallback script.")
        return _get_fallback_script(theme)
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        prompt = INSPIRATION_USER_PROMPT.format(
            theme=theme["theme"],
            principle=theme["principle"],
            philosophers=", ".join(theme["philosophers"])
        )
        
        print("  🤖 Generating inspiration script with Gemini 2.5 Flash...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": INSPIRATION_SYSTEM_PROMPT,
                "temperature": 0.9,  # Slightly lower than story mode for consistency
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
            philosopher = data.get("philosopher", theme["philosophers"][0]).strip()
            
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
            # Trim at sentence boundary
            words = script.split()
            trimmed = ' '.join(words[:100])
            boundaries = [trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?')]
            last_boundary = max(boundaries)
            if last_boundary > int(len(trimmed) * 0.7):
                script = trimmed[:last_boundary + 1]
            else:
                script = trimmed
            print(f"  ⚠️ Script was {word_count} words — trimmed to {len(script.split())}")
        
        print(f"  ✅ Inspiration script generated!")
        print(f"     Headline: \"{headline}\"")
        print(f"     Philosopher: {philosopher}")
        print(f"     Words: {len(script.split())}")
        
        return headline, script, philosopher, theme_name
        
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
            "headline": "SILENCE IS POWER",
            "script": "Stop explaining yourself. The people who matter... don't need it. And the ones who don't matter... won't believe it anyway. Marcus Aurelius ruled the most powerful empire on Earth. Yet he never raised his voice. He understood something most people never will. Your silence, is louder than their noise. The next time someone tries to drag you into chaos, ask yourself... is this under my control? If the answer is no, let it go. Type STRENGTH if you choose peace over drama today.",
            "philosopher": "Marcus Aurelius",
        },
        {
            "headline": "STOP BEING TOO NICE",
            "script": "Kindness without boundaries, isn't kindness. It's self-destruction. Seneca watched the most generous men in Rome... get eaten alive by the people they helped. You're not being noble. You're being a doormat. Real strength is saying no, without guilt. Real power is walking away, without looking back. The people who drain you... don't deserve your energy. Protect your peace like your life depends on it. Because it does. Save this for when you need a reminder.",
            "philosopher": "Seneca",
        },
        {
            "headline": "YOUR ANGER DESTROYS YOU",
            "script": "Every second you stay angry... is a second of peace you'll never get back. Seneca said it best. Anger is an acid, that does more harm to the vessel that holds it. You think you're punishing them. You're punishing yourself. They're sleeping fine. You're the one lying awake. Drop the grudge. Not for them... for you. The strongest revenge is a life well lived. Follow for your daily Stoic lesson.",
            "philosopher": "Seneca",
        },
    ]
    
    chosen = random.choice(fallback_scripts)
    return chosen["headline"], chosen["script"], chosen["philosopher"], theme["theme"]


if __name__ == "__main__":
    # Test with a random theme
    headline, script, philosopher, theme_name = generate_inspiration_script()
    print(f"\n--- RESULT ---")
    print(f"THEME: {theme_name}")
    print(f"HEADLINE: {headline}")
    print(f"PHILOSOPHER: {philosopher}")
    print(f"SCRIPT: {script}")
    print(f"WORDS: {len(script.split())}")
