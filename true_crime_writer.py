"""
True Crime / Scary Story Script Writer — Generates eerie horror narration scripts for YouTube Shorts.

Dual source:
1. PRIMARY: Scrapes from Reddit horror subs (r/nosleep, r/LetsNotMeet, r/creepyencounters,
   r/TrueScaryStories) via RSS — same approach as scraper.py
2. FALLBACK: AI-generated horror fiction if no good stories found

Uses Google Gemini 2.5 Flash (free tier) to rewrite scraped stories into maximum-dread scripts.

Content safety: All stories are user-submitted fiction or real accounts (public domain).
No copyrighted true crime reporting is used.

Requires: GEMINI_API_KEY environment variable
Fallback: Returns a pre-written fallback script if everything fails
"""
import os
import sys
import re
import json
import html
import random
import xml.etree.ElementTree as ET
import requests

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# --- Horror Subreddits ---
# These subs contain user-submitted scary stories (fiction and real accounts).
# All content is public domain — no copyrighted true crime reporting.
HORROR_SUBREDDITS = [
    "nosleep",
    "LetsNotMeet",
    "creepyencounters",
    "TrueScaryStories",
    "Thetruthishere",
    "Glitch_in_the_Matrix",
    "shortscarystories",
    "TwoSentenceHorror",
]

# Words that signal high-dread, high-engagement stories
HORROR_KEYWORDS = [
    "stalker", "followed", "dark", "night", "door", "knock", "dead",
    "scream", "blood", "shadow", "disappeared", "missing", "basement",
    "window", "locked", "alone", "heard", "whisper", "footsteps",
    "watching", "behind", "eyes", "mirror", "phone", "called",
    "stranger", "broke in", "never found", "no explanation", "still",
    "haunted", "ghost", "creature", "woods", "road", "abandoned",
]

# Words that indicate gore/extreme content we should avoid
SKIP_KEYWORDS = [
    'suicide', 'self harm', 'eating disorder', 'child abuse',
    'sexual assault', 'rape', 'graphic violence',
]

# --- AI-Generated Horror Topics (for when scraping fails) ---
AI_HORROR_TOPICS = [
    {"topic": "The Babysitter Call", "setup": "A babysitter receives a phone call from inside the house.", "mood": "classic horror"},
    {"topic": "Highway Stranger", "setup": "A driver picks up a hitchhiker on a deserted highway at 2 AM.", "mood": "isolation"},
    {"topic": "The New Apartment", "setup": "Strange things happen in a newly rented apartment — previous tenant disappeared.", "mood": "domestic horror"},
    {"topic": "Night Shift Security", "setup": "A night security guard sees something impossible on the cameras.", "mood": "workplace horror"},
    {"topic": "The Camping Trip", "setup": "Friends camping in the woods find signs someone has been watching them.", "mood": "wilderness horror"},
    {"topic": "Wrong Number", "setup": "Someone keeps calling from a number that belongs to a person who died 3 years ago.", "mood": "supernatural"},
    {"topic": "The Uber Ride", "setup": "A late-night Uber takes a route through an area that doesn't exist on the map.", "mood": "modern horror"},
    {"topic": "The Mirror", "setup": "The reflection in the bathroom mirror moves a fraction of a second too late.", "mood": "psychological"},
    {"topic": "The Recording", "setup": "A voice recorder left running overnight captures sounds that shouldn't be there.", "mood": "found footage"},
    {"topic": "The Neighbor's Dog", "setup": "The neighbor's dog barks at the same spot in the yard every night — where the previous owner was buried.", "mood": "suburban horror"},
    {"topic": "Sleep Paralysis Entity", "setup": "Every night, the same figure stands at the foot of the bed. Then it starts getting closer.", "mood": "psychological"},
    {"topic": "The Trail Camera", "setup": "A hunter reviews trail camera footage and finds images of someone watching his cabin.", "mood": "wilderness horror"},
    {"topic": "The Storage Unit", "setup": "A storage unit auction reveals a space that someone has clearly been living in.", "mood": "mystery horror"},
    {"topic": "The Last Text", "setup": "A missing person's phone sends one final text: 'Don't come looking for me. They'll find you too.'", "mood": "modern horror"},
    {"topic": "The House Tour", "setup": "A real estate agent showing an empty house realizes someone is already inside.", "mood": "domestic horror"},
]

# System prompt for rewriting scraped stories
TRUE_CRIME_REWRITE_PROMPT = """You are the #1 viral "Scary Story" YouTube Shorts scriptwriter. Your horror narrations consistently hit 15M+ views because they create genuine DREAD in under 45 seconds.

YOUR STYLE: Slow, atmospheric, whispery. Think "someone telling a ghost story around a campfire at midnight." Your tone is calm but increasingly unsettling. The horror should creep in, not jump-scare.

THE PERFECT SCRIPT STRUCTURE:

1. HOOK (1 sentence, 0-3 seconds): Drop the viewer into the scariest moment. Use present tense for immediacy. "The scratching starts at exactly 2 AM. Every. Single. Night." / "I should never have opened that door." NEVER start with "So" or "This happened to me". Start with the fear.

2. BUILD-UP (4-6 sentences, 3-30 seconds): Slow, atmospheric tension. Short sentences. Strategic ellipses (...) for pauses. Each sentence should make the viewer slightly more uncomfortable. Use sensory details: what you HEARD, what you SAW, what you FELT. 

3. CLIMAX CLIFFHANGER (1-2 sentences, 30-40 seconds): End at PEAK tension with NO resolution. The video must end BEFORE the viewer gets answers. "And when I finally turned around..." / "The last thing I saw before the lights went out..." This forces rewatches and loop completions.

CRITICAL RULES:
1. 100-120 words EXACTLY. Slightly longer than other formats — horror needs build-up.
2. NO AI clichés: Never use "Little did I know", "What happened next changed everything", "I'll never forget".
3. SLOW BURN: Do NOT reveal the horror too early. Build tension gradually. The first 15 seconds should feel normal, slightly off.
4. USE ELLIPSES: Strategic "..." creates natural pauses that make the TTS voice sound genuinely hesitant and scared.
5. PRESENT TENSE: Write as if it's happening RIGHT NOW for maximum immersion.
6. NO EMOJIS, NO BRACKETS, NO MARKDOWN: Pure spoken text only.
7. PROPER APOSTROPHES: Always write "don't" not "dont", "I'm" not "im".
8. LEAVE THEM HANGING: The viewer must feel UNSATISFIED at the end. No answers. No resolution."""

TRUE_CRIME_REWRITE_USER = """Rewrite this scary story into a viral YouTube Shorts horror narration:

Original title: {title}
Original story: {body}

Respond ONLY with a valid JSON object:
{{
  "headline": "A creepy ALL CAPS title (4-8 words). Examples: 'I SHOULD NEVER HAVE OPENED THAT DOOR', 'THE SCRATCHING STARTS AT 2 AM'",
  "script": "The full horror narration (100-120 words). Hook → Build-up → Cliffhanger ending with NO resolution."
}}"""

# System prompt for AI-generated horror (when scraping fails)
TRUE_CRIME_GENERATE_PROMPT = """You are the #1 viral "Scary Story" YouTube Shorts scriptwriter. Your horror narrations consistently hit 15M+ views because they create genuine DREAD in under 45 seconds.

YOUR STYLE: Slow, atmospheric, whispery. Think "someone telling a ghost story around a campfire at midnight." Your tone is calm but increasingly unsettling.

Write a complete, self-contained horror micro-story. First person. Present tense. The horror should creep in slowly, then end at peak tension with NO resolution.

CRITICAL RULES:
1. 100-120 words EXACTLY.
2. Start with the scariest moment, then build context.
3. End at PEAK TENSION. No resolution. No answers. The viewer must rewatch.
4. Use ellipses (...) for pauses. Short sentences. Sensory details.
5. NO EMOJIS, NO BRACKETS, NO MARKDOWN: Pure spoken text only.
6. PROPER APOSTROPHES: "don't" not "dont"."""

TRUE_CRIME_GENERATE_USER = """Write a viral horror YouTube Shorts narration about this scenario:

SCENARIO: {setup}
MOOD: {mood}
TOPIC: {topic}

Respond ONLY with a valid JSON object:
{{
  "headline": "A creepy ALL CAPS title (4-8 words). Examples: 'THE DOOR WAS ALREADY OPEN', 'SOMETHING LIVES IN MY WALLS'",
  "script": "The full horror narration (100-120 words). Hook → Slow build → Cliffhanger."
}}"""


def clean_text(text):
    """Removes URLs and weird characters that TTS might struggle with."""
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s.,!?\'\"-]', '', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def score_horror_story(title, body):
    """
    Scores a horror story's viral potential.
    Higher score = more atmospheric, more dread.
    """
    score = 0
    combined = (title + " " + body).lower()

    # Horror keyword density
    keyword_hits = sum(1 for kw in HORROR_KEYWORDS if kw in combined)
    score += keyword_hits * 6

    # Short punchy opening
    sentences = re.split(r'[.!?]+', body.strip())
    if sentences and len(sentences[0].split()) < 12:
        score += 10

    # First person (more immersive)
    if combined[:50].count(' i ') >= 1 or combined.startswith('i '):
        score += 8

    # Present tense indicators
    present_tense = ['i hear', 'i see', 'i feel', 'there is', "it's", "i'm"]
    score += sum(3 for pt in present_tense if pt in combined)

    return score


def scrape_horror_story():
    """
    Scrapes a scary story from Reddit horror subs using RSS.
    Same approach as scraper.py but targeting horror-specific subs.

    Returns: (title, body, subreddit) or (None, None, None) if nothing found
    """
    headers = {
        'User-Agent': 'python:yt_automater_bot:v3.0 (by /u/automation)'
    }

    all_posts = []
    subs_to_try = random.sample(HORROR_SUBREDDITS, min(4, len(HORROR_SUBREDDITS)))

    for subreddit in subs_to_try:
        sort_type = random.choice(["top", "top", "rising"])

        if sort_type == "top":
            timeframe = random.choice(["day", "week"])
            url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t={timeframe}"
            print(f"  Fetching horror from r/{subreddit} (Top {timeframe}) via RSS...")
        else:
            url = f"https://www.reddit.com/r/{subreddit}/rising/.rss"
            print(f"  Fetching horror from r/{subreddit} (Rising) via RSS...")

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text
                content_elem = entry.find('atom:content', ns)

                if content_elem is not None and content_elem.text:
                    body_html = html.unescape(content_elem.text)
                    body_text = re.sub(r'<[^>]+>', ' ', body_html)
                    body_text = re.sub(r'\s+', ' ', body_text)
                    body_text = re.sub(
                        r'submitted by /u/\S+ \[link\] \[comments\]', '', body_text
                    ).strip()

                    body_lower = body_text.lower()
                    title_lower = title.lower()

                    # Skip sensitive content
                    if any(word in body_lower for word in SKIP_KEYWORDS) or \
                       any(word in title_lower for word in SKIP_KEYWORDS):
                        continue

                    word_count = len(body_text.split())

                    # Target 80-300 words (shorter is better for horror)
                    if 80 < word_count < 300:
                        horror_score = score_horror_story(title, body_text)
                        all_posts.append({
                            'title': title,
                            'body': body_text,
                            'subreddit': subreddit,
                            'score': horror_score
                        })

        except Exception as e:
            print(f"  Error fetching from r/{subreddit}: {e}")

    if all_posts:
        all_posts.sort(key=lambda x: x['score'], reverse=True)

        # Filter out low-scoring stories
        MIN_HORROR_SCORE = 15
        strong_posts = [p for p in all_posts if p['score'] >= MIN_HORROR_SCORE]
        if not strong_posts:
            strong_posts = all_posts[:3]

        top_candidates = strong_posts[:min(3, len(strong_posts))]
        chosen = random.choice(top_candidates)

        print(f"\n  ✅ Selected horror story from r/{chosen['subreddit']} "
              f"(horror score: {chosen['score']})")

        return (
            clean_text(chosen['title']),
            clean_text(chosen['body']),
            chosen['subreddit']
        )

    return None, None, None


def generate_true_crime_script(used_topics=None):
    """
    Generates a True Crime / Scary Story script.

    Strategy:
    1. Try scraping a real story from Reddit horror subs
    2. If found, rewrite it with Gemini for maximum dread
    3. If scraping fails, generate an original AI horror story

    Args:
        used_topics: List of recently used topic names to avoid repetition

    Returns:
        tuple: (headline, script, source_sub_or_topic, theme_name)
        Falls back to pre-written scripts if everything fails
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    # Step 1: Try scraping a real story
    print("\n  👻 Searching Reddit for scary stories...")
    title, body, subreddit = scrape_horror_story()

    if title and body:
        print(f"  📖 Found story: {title[:60]}")
        print(f"  📍 From: r/{subreddit}")
        print(f"  📏 Length: {len(body.split())} words")

        # Step 2: Rewrite with AI if possible
        if api_key:
            result = _rewrite_with_ai(api_key, title, body)
            if result:
                headline, script = result
                return headline, script, subreddit, f"reddit_{subreddit}"
        
        # Fallback: Use raw story with basic cleanup
        print("  ⚠️ Using raw Reddit story (no AI rewrite)")
        # Truncate if too long
        words = body.split()
        if len(words) > 120:
            body = ' '.join(words[:120])
            boundaries = [body.rfind('.'), body.rfind('!'), body.rfind('?')]
            last = max(boundaries)
            if last > len(body) * 0.7:
                body = body[:last + 1]
        return title.upper()[:50], body, subreddit, f"reddit_{subreddit}"

    # Step 3: Scraping failed — generate AI horror story
    print("  ⚠️ No suitable Reddit horror stories found")
    print("  🤖 Generating AI horror story instead...")

    if api_key:
        result = _generate_ai_horror(api_key, used_topics)
        if result:
            return result

    # Step 4: Everything failed — use fallback
    print("  ⚠️ Using pre-written fallback horror script")
    return _get_fallback_script()


def _rewrite_with_ai(api_key, title, body):
    """Rewrites a scraped horror story with Gemini AI."""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = TRUE_CRIME_REWRITE_USER.format(title=title, body=body)

        print("  🤖 Rewriting horror story with Gemini 2.5 Flash...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": TRUE_CRIME_REWRITE_PROMPT,
                "temperature": 0.9,
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

        data = json.loads(result_text)
        headline = data.get("headline", title.upper()).strip()
        script = data.get("script", "").strip()

        if not script:
            return None

        # Clean up
        headline = re.sub(r'[*#_]', '', headline).strip('"').strip("'")
        script = re.sub(r'[*#_]', '', script)

        # Validate word count
        word_count = len(script.split())
        if word_count > 135:
            words = script.split()
            trimmed = ' '.join(words[:120])
            boundaries = [trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?')]
            last_boundary = max(boundaries)
            if last_boundary > int(len(trimmed) * 0.7):
                script = trimmed[:last_boundary + 1]
            else:
                script = trimmed
            print(f"  ⚠️ Script was {word_count} words — trimmed to {len(script.split())}")

        print(f"  ✅ Horror script rewritten!")
        print(f"     Headline: \"{headline}\"")
        print(f"     Words: {len(script.split())}")

        return headline, script

    except Exception as e:
        print(f"  ⚠️ AI rewrite failed: {e}")
        return None


def _generate_ai_horror(api_key, used_topics=None):
    """Generates an original AI horror story when scraping fails."""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        # Pick a topic, avoiding recently used ones
        available = AI_HORROR_TOPICS
        if used_topics:
            available = [t for t in AI_HORROR_TOPICS if t["topic"] not in used_topics]
            if not available:
                available = AI_HORROR_TOPICS

        topic = random.choice(available)
        print(f"  🎭 Selected horror topic: \"{topic['topic']}\"")

        prompt = TRUE_CRIME_GENERATE_USER.format(
            setup=topic["setup"],
            mood=topic["mood"],
            topic=topic["topic"]
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": TRUE_CRIME_GENERATE_PROMPT,
                "temperature": 1.0,
                "max_output_tokens": 400,
                "response_mime_type": "application/json",
            }
        )

        result_text = response.text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        elif result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        data = json.loads(result_text)
        headline = data.get("headline", topic["topic"].upper()).strip()
        script = data.get("script", "").strip()

        if not script:
            return None

        headline = re.sub(r'[*#_]', '', headline).strip('"').strip("'")
        script = re.sub(r'[*#_]', '', script)

        # Validate word count
        word_count = len(script.split())
        if word_count > 135:
            words = script.split()
            trimmed = ' '.join(words[:120])
            boundaries = [trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?')]
            last_boundary = max(boundaries)
            if last_boundary > int(len(trimmed) * 0.7):
                script = trimmed[:last_boundary + 1]
            else:
                script = trimmed

        print(f"  ✅ AI horror story generated!")
        print(f"     Headline: \"{headline}\"")
        print(f"     Words: {len(script.split())}")

        return headline, script, f"ai_{topic['mood']}", topic["topic"]

    except Exception as e:
        print(f"  ⚠️ AI horror generation failed: {e}")
        return None


def _get_fallback_script():
    """Returns a pre-written fallback script when everything fails."""
    fallback_scripts = [
        {
            "headline": "THE SCRATCHING STARTS AT 2 AM",
            "script": "The scratching starts at exactly 2 AM. Every single night. Three slow drags across the wall behind my bed. I told myself it was mice. I told myself it was pipes. Then last Tuesday... I pressed my ear against the wall. And the scratching stopped. For three seconds, there was nothing. Just silence. Then... a whisper. Right on the other side of the drywall. My name. Slowly. Deliberately. Like someone tasting each syllable. I checked with my landlord. There's no unit on the other side of that wall. It's solid brick. Six inches of it. But tonight... tonight the scratching is louder.",
            "source": "ai_domestic_horror",
            "theme": "The Wall",
        },
        {
            "headline": "I SHOULD NEVER HAVE ANSWERED",
            "script": "My phone rings at 3:17 AM. Unknown number. I answer because... I don't know why I answer. The voice on the other end is mine. Not similar. Not an impression. My exact voice. It says, don't go to work tomorrow. Then it hangs up. I check my call log. The call lasted 4 seconds. The number... is my own number. I didn't call myself. I star 69 the call. The automated voice says, the number you are trying to reach... has been disconnected. I look at my phone. The call log entry is gone. Like it never happened. But I remember it. And tomorrow is Monday.",
            "source": "ai_supernatural",
            "theme": "Wrong Number",
        },
        {
            "headline": "SOMETHING LIVES IN MY BASEMENT",
            "script": "I've lived alone for six years. The basement door stays locked. Always. Last week, I noticed the lock was on the wrong side. It wasn't keeping something out. It was keeping something in. I laughed it off. Old house, previous owner was probably paranoid. Then I found the logbook behind the water heater. Dates going back to 1987. Each entry the same format. A date... and a single word. Fed. The last entry was three weeks ago. Three weeks before I moved in. I counted the days between entries. Every 21 days. Like clockwork. Today... is day 21.",
            "source": "ai_domestic_horror",
            "theme": "The Basement",
        },
    ]

    chosen = random.choice(fallback_scripts)
    return chosen["headline"], chosen["script"], chosen["source"], chosen["theme"]


if __name__ == "__main__":
    headline, script, source, theme_name = generate_true_crime_script()
    print(f"\n--- RESULT ---")
    print(f"THEME: {theme_name}")
    print(f"SOURCE: {source}")
    print(f"HEADLINE: {headline}")
    print(f"SCRIPT: {script}")
    print(f"WORDS: {len(script.split())}")
