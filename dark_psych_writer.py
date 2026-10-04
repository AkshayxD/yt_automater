"""
Dark Psychology Script Writer — Generates dark psychology / "Did You Know" fact scripts for YouTube Shorts.

Uses Google Gemini 2.5 Flash (free tier: 15 RPM, 1500 RPD) to create:
1. A bold, authoritative headline (ALL CAPS, 4-8 words)
2. A Hook → Fact → Application → CTA structure
3. Based on real psychological principles (public domain knowledge)

Content is 100% original — AI explains well-documented psychology concepts.
No scraping needed. Pure AI generation with rotating topics.

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

# --- Dark Psychology Topic Bank ---
# 30 rotating topics to prevent repetition across days.
# Each topic has the psychological principle and a real-world context.
DARK_PSYCH_TOPICS = [
    {"topic": "The Door-in-the-Face Technique", "principle": "Ask for something huge first, get rejected, then ask for what you actually want — it feels reasonable by comparison.", "field": "Social Psychology"},
    {"topic": "Love Bombing", "principle": "Narcissists overwhelm you with attention and affection early on to create emotional dependency before the abuse starts.", "field": "Narcissism"},
    {"topic": "The Benjamin Franklin Effect", "principle": "If someone does YOU a favor, they like you MORE — not less. Their brain rationalizes the effort by deciding you must be worth it.", "field": "Cognitive Bias"},
    {"topic": "Mirror Neurons and Manipulation", "principle": "Manipulators mimic your body language and speech patterns to create artificial trust and intimacy.", "field": "Neuroscience"},
    {"topic": "The Halo Effect", "principle": "Attractive people are automatically assumed to be smarter, kinder, and more trustworthy — even with zero evidence.", "field": "Cognitive Bias"},
    {"topic": "Gaslighting Patterns", "principle": "Gaslighters deny your reality so often that you start doubting your own memory and perception.", "field": "Manipulation"},
    {"topic": "The Scarcity Principle", "principle": "When something seems rare or limited, we want it more — even if we didn't want it before.", "field": "Persuasion"},
    {"topic": "Intermittent Reinforcement", "principle": "Unpredictable rewards create stronger addiction than consistent ones — this is why toxic relationships are so hard to leave.", "field": "Behavioral Psychology"},
    {"topic": "The Dunning-Kruger Effect", "principle": "The less someone knows, the more confident they are. The more they know, the more they doubt themselves.", "field": "Cognitive Bias"},
    {"topic": "Emotional Vampires", "principle": "Some people unconsciously drain your energy by always being in crisis, making every conversation about themselves.", "field": "Social Psychology"},
    {"topic": "The Foot-in-the-Door Technique", "principle": "Get someone to agree to a small request first, and they're far more likely to agree to a big one later.", "field": "Persuasion"},
    {"topic": "Projection as Defense", "principle": "When someone accuses you of something you didn't do, they're often revealing what THEY are doing.", "field": "Defense Mechanisms"},
    {"topic": "The Zeigarnik Effect", "principle": "Your brain remembers unfinished tasks far better than completed ones — this is why cliffhangers work.", "field": "Cognitive Psychology"},
    {"topic": "Triangulation", "principle": "Manipulators bring a third person into the dynamic to make you feel jealous, insecure, or to validate their position.", "field": "Narcissism"},
    {"topic": "The Spotlight Effect", "principle": "You think everyone is watching and judging you. In reality, people barely notice — they're too busy worrying about themselves.", "field": "Social Psychology"},
    {"topic": "Sunk Cost Fallacy", "principle": "You stay in bad situations because you've already invested so much time, money, or emotion — even when leaving is clearly better.", "field": "Decision Making"},
    {"topic": "Dark Triad Personalities", "principle": "Narcissism, Machiavellianism, and Psychopathy — people with all three are charming, strategic, and completely ruthless.", "field": "Personality Psychology"},
    {"topic": "The Pratfall Effect", "principle": "Highly competent people become MORE likeable when they make a small mistake — it makes them relatable.", "field": "Social Psychology"},
    {"topic": "Weaponized Silence", "principle": "The silent treatment is not just 'needing space' — it's a calculated punishment designed to make you anxious and desperate.", "field": "Manipulation"},
    {"topic": "Anchoring Bias", "principle": "The first number you hear sets your mental benchmark. Skilled negotiators always throw out an extreme number first.", "field": "Cognitive Bias"},
    {"topic": "The 48 Laws of Power - Law 3", "principle": "Conceal your intentions. If people know what you want, they can use it against you or block your path.", "field": "Strategy"},
    {"topic": "Cognitive Dissonance", "principle": "When your actions contradict your beliefs, your brain changes your beliefs to match — not the other way around.", "field": "Cognitive Psychology"},
    {"topic": "The Grey Rock Method", "principle": "The best way to deal with a narcissist is to become boring. Give them no emotional reaction and they lose interest.", "field": "Self-Defense"},
    {"topic": "Social Proof Manipulation", "principle": "We assume something is correct if other people are doing it. Cults, scams, and trends all exploit this instinct.", "field": "Persuasion"},
    {"topic": "The Contrast Principle", "principle": "Show someone something terrible first, and the mediocre option looks amazing by comparison. Used in sales, negotiations, and relationships.", "field": "Persuasion"},
    {"topic": "Trauma Bonding", "principle": "Abuse followed by kindness creates a powerful emotional bond that's stronger than normal relationships — this is why victims stay.", "field": "Trauma Psychology"},
    {"topic": "The Bystander Effect", "principle": "The more people witness an emergency, the LESS likely anyone is to help. Everyone assumes someone else will act.", "field": "Social Psychology"},
    {"topic": "Machiavellian Intelligence", "principle": "The most socially successful people are often the best manipulators — they read the room and play the game without you knowing.", "field": "Personality Psychology"},
    {"topic": "The Reciprocity Trap", "principle": "When someone gives you a gift, you feel obligated to return the favor — even if the gift was unwanted. Manipulators exploit this constantly.", "field": "Social Psychology"},
    {"topic": "Learned Helplessness", "principle": "If you're punished no matter what you do, eventually you stop trying altogether — even when escape becomes possible.", "field": "Behavioral Psychology"},
]

# System prompt optimized for Dark Psychology scripts
DARK_PSYCH_SYSTEM_PROMPT = """You are the #1 viral "Dark Psychology" YouTube Shorts scriptwriter. Your videos consistently hit 10M+ views because they make viewers feel like they've just unlocked a secret the world doesn't want them to know.

YOUR STYLE: Authoritative, slightly ominous, revealing. Think "professor who knows too much" meets "friend warning you about danger." Your tone says: "I'm about to tell you something that will change how you see everyone around you."

THE PERFECT SCRIPT STRUCTURE:

1. HOOK (1 sentence, 0-3 seconds): A bold claim that STOPS the scroll. "If someone does THIS to you, they're manipulating you." / "This psychological trick controls 90% of people." / "Never trust someone who does this." NEVER start with "Did you know" or "Fun fact". The hook must feel like a WARNING.

2. THE FACT (3-5 sentences, 3-25 seconds): Explain the psychological principle clearly. Use a vivid, relatable, real-world example. Name the technique. Make the viewer recognize it from their own life. "It's called [technique name], and it works because..." Keep sentences SHORT (≤12 words).

3. APPLICATION (1-2 sentences, 25-32 seconds): Tell the viewer how to spot it or use this knowledge. "Next time someone does X, now you know exactly what's happening." / "The counter? Do THIS instead."

4. CTA (1 sentence, 32-38 seconds): End with a strong hook to subscribe. Rotate styles: "Subscribe so you don't miss the next one.", "Hit that subscribe button for daily psychology.", "Subscribe to stay one step ahead."

CRITICAL RULES:
1. 80-100 words EXACTLY. Short = loopable = viral.
2. NO AI clichés: Never use "In a world where...", "Let that sink in", "Here's the thing".
3. NAME THE TECHNIQUE: Always mention the actual psychology term — it adds authority.
4. MAKE IT FEEL DANGEROUS: The viewer should feel like they're learning a forbidden secret.
5. NO EMOJIS, NO BRACKETS, NO MARKDOWN: Pure spoken text only.
6. PROPER APOSTROPHES: Always write "don't" not "dont", "they're" not "theyre".
7. DARK BUT NOT EVIL: You're teaching AWARENESS, not manipulation. Frame it as self-defense."""

DARK_PSYCH_USER_PROMPT = """Write a viral "Dark Psychology" YouTube Shorts script about this topic:

TOPIC: {topic}
PRINCIPLE: {principle}
FIELD: {field}

Respond ONLY with a valid JSON object:
{{
  "headline": "A punchy ALL CAPS title (4-8 words). Examples: 'NEVER TRUST SOMEONE WHO DOES THIS', 'THIS TRICK CONTROLS YOUR MIND'",
  "script": "The full spoken script (80-100 words). Hook → Fact → Application → Subscribe CTA.",
  "topic": "The psychology topic name (e.g., 'The Halo Effect')"
}}"""


def get_unused_topic(used_topics=None):
    """
    Picks a Dark Psychology topic that hasn't been used recently.

    Args:
        used_topics: List of recently used topic names to avoid

    Returns:
        dict with 'topic', 'principle', 'field' keys
    """
    if not used_topics:
        return random.choice(DARK_PSYCH_TOPICS)

    available = [t for t in DARK_PSYCH_TOPICS if t["topic"] not in used_topics]

    if not available:
        print("  ♻️ All Dark Psychology topics exhausted — resetting rotation")
        available = DARK_PSYCH_TOPICS

    return random.choice(available)


def generate_dark_psych_script(used_topics=None):
    """
    Generates a Dark Psychology script using Gemini AI.

    Args:
        used_topics: List of recently used topic names to avoid repetition

    Returns:
        tuple: (headline, script, topic_name, theme_name)
        Falls back to a pre-written script if API is unavailable
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    topic = get_unused_topic(used_topics)
    topic_name = topic["topic"]
    print(f"  🧠 Selected Dark Psychology topic: \"{topic_name}\"")
    print(f"     Field: {topic['field']}")

    if not api_key:
        print("  ⚠️ GEMINI_API_KEY not found! Using fallback script.")
        return _get_fallback_script(topic)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = DARK_PSYCH_USER_PROMPT.format(
            topic=topic["topic"],
            principle=topic["principle"],
            field=topic["field"]
        )

        print("  🤖 Generating Dark Psychology script with Gemini 2.5 Flash...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": DARK_PSYCH_SYSTEM_PROMPT,
                "temperature": 0.85,  # Slightly lower for factual accuracy
                "max_output_tokens": 400,
                "response_mime_type": "application/json",
            }
        )

        result_text = response.text.strip()

        # Clean markdown code blocks
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        elif result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        try:
            data = json.loads(result_text)
            headline = data.get("headline", topic_name.upper()).strip()
            script = data.get("script", "").strip()
            returned_topic = data.get("topic", topic_name).strip()

            if not script:
                print("  ⚠️ AI returned empty script! Using fallback.")
                return _get_fallback_script(topic)
        except json.JSONDecodeError as e:
            print(f"  ⚠️ Failed to parse JSON: {e}, using fallback")
            print(f"  Raw response: {result_text[:200]}")
            return _get_fallback_script(topic)

        # Clean up formatting
        headline = re.sub(r'[*#_]', '', headline).strip('"').strip("'")
        script = re.sub(r'[*#_]', '', script)

        # Validate word count
        word_count = len(script.split())
        if word_count > 115:
            words = script.split()
            trimmed = ' '.join(words[:100])
            boundaries = [trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?')]
            last_boundary = max(boundaries)
            if last_boundary > int(len(trimmed) * 0.7):
                script = trimmed[:last_boundary + 1]
            else:
                script = trimmed
            print(f"  ⚠️ Script was {word_count} words — trimmed to {len(script.split())}")

        print(f"  ✅ Dark Psychology script generated!")
        print(f"     Headline: \"{headline}\"")
        print(f"     Topic: {returned_topic}")
        print(f"     Words: {len(script.split())}")

        return headline, script, returned_topic, topic_name

    except ImportError:
        print("  ⚠️ google-genai not installed — using fallback")
        return _get_fallback_script(topic)
    except Exception as e:
        print(f"  ⚠️ Gemini API error: {e} — using fallback")
        return _get_fallback_script(topic)


def _get_fallback_script(topic):
    """Returns a pre-written fallback script when the API is unavailable."""
    fallback_scripts = [
        {
            "headline": "NEVER TRUST SOMEONE WHO DOES THIS",
            "script": "If someone mirrors your body language perfectly... they might be manipulating you. It's called the Mirror Neuron Technique. Skilled manipulators copy your gestures, your speech patterns, even your breathing rate. Your brain interprets this as, this person is just like me. And you drop your guard. Completely. Salespeople do it. Con artists do it. Narcissists do it on first dates. The counter? Change your posture suddenly. Cross your arms. If they copy you within 5 seconds... they're not connecting with you. They're studying you. Save this. You'll need it.",
            "topic": "Mirror Neurons and Manipulation",
        },
        {
            "headline": "WHY YOU CAN'T LEAVE TOXIC PEOPLE",
            "script": "The reason you can't leave that toxic relationship... has nothing to do with love. It's called Intermittent Reinforcement. When someone is cruel to you, then suddenly sweet, your brain releases MORE dopamine than if they were consistently kind. It's the same mechanism behind slot machines. Unpredictable rewards create the strongest addiction. That's why their rare kindness feels more intense than someone who's good to you every day. Your brain is literally addicted to the chaos. Recognizing the pattern is the first step to breaking it. Follow for daily psychology.",
            "topic": "Intermittent Reinforcement",
        },
        {
            "headline": "THIS TRICK CONTROLS YOUR DECISIONS",
            "script": "The first number you hear... controls every number after it. It's called Anchoring Bias. A car dealer shows you a 50,000 dollar car first. Then shows you one for 30,000. Suddenly 30,000 feels like a steal. But it's not. They just made your brain anchor to the higher number. Restaurants do this too. The most expensive item on the menu exists to make the second most expensive look reasonable. Next time someone throws out a big number first... pause. They're not informing you. They're anchoring you. Share this with someone who needs it.",
            "topic": "Anchoring Bias",
        },
        {
            "headline": "THE MOST DANGEROUS PERSONALITY TYPE",
            "script": "If someone is charming, strategic, and completely emotionless under pressure... be careful. They might have what psychologists call the Dark Triad. That's Narcissism, Machiavellianism, and Psychopathy, all in one person. They read the room perfectly. They know exactly what you want to hear. And they'll say it without meaning a single word. These people rise fast in business, politics, and relationships. You won't spot them by their behavior. You'll spot them by how you FEEL around them. Drained. Confused. Second-guessing yourself. Trust that feeling. Save this.",
            "topic": "Dark Triad Personalities",
        },
        {
            "headline": "STOP FALLING FOR THIS TRICK",
            "script": "When someone gives you something you didn't ask for... be cautious. It's called the Reciprocity Trap. A free sample at the store. An unexpected compliment from a stranger. A gift from someone who wants something. Your brain is wired to return favors. Even unwanted ones. Manipulators exploit this instinct constantly. They give first, creating a debt you never agreed to. Then they cash in. And if you say no? They guilt you. You owe me. Remember, you don't owe anyone anything for gifts you didn't request. Follow for daily psychology.",
            "topic": "The Reciprocity Trap",
        },
    ]

    chosen = random.choice(fallback_scripts)
    return chosen["headline"], chosen["script"], chosen["topic"], topic["topic"]


if __name__ == "__main__":
    headline, script, topic_returned, topic_name = generate_dark_psych_script()
    print(f"\n--- RESULT ---")
    print(f"TOPIC: {topic_name}")
    print(f"HEADLINE: {headline}")
    print(f"PSYCHOLOGY TOPIC: {topic_returned}")
    print(f"SCRIPT: {script}")
    print(f"WORDS: {len(script.split())}")
