import sys
import requests
import random
import re
import html
import xml.etree.ElementTree as ET

# Fix Windows console encoding for emoji in log output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# --- Viral Scoring Configuration ---

# Words that signal high-drama, high-engagement stories
VIRAL_KEYWORDS = [
    "revenge", "fired", "caught", "cheating", "divorced", "police", "arrested",
    "boss", "wedding", "karma", "exposed", "confronted", "screamed", "lawsuit",
    "kicked out", "uninvited", "destroyed", "secret", "betrayed", "pregnant",
    "stolen", "lied", "snapped", "quit", "inheritance", "neighbor", "entitled",
    "karen", "mother-in-law", "teacher", "roommate", "ex", "ultimatum"
]

# Words that indicate a sad vent rather than an entertaining story
BORING_KEYWORDS = [
    'tired', 'depressed', 'suicide', 'kill myself', 'give up', 'sad',
    'crying', 'lonely', 'anxiety', 'therapy', 'grief', 'mourning',
    'self harm', 'eating disorder', 'mental health'
]

# Subreddits proven to have viral-worthy story content
SUBREDDITS = [
    "pettyrevenge", "ProRevenge", "NuclearRevenge", "MaliciousCompliance",
    "confession", "tifu", "EntitledParents", "TrueOffMyChest",
    "AmItheAsshole", "ChoosingBeggars", "IDontWorkHereLady",
    "relationships", "neighborsfromhell", "BestofRedditorUpdates"
]


def clean_text(text):
    """Removes URLs and weird characters that TTS might struggle with."""
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s.,!?\'\"-]', '', text)
    # Collapse multiple spaces
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def score_story_virality(title, body):
    """
    Scores a story's viral potential based on multiple engagement signals.
    Higher score = more likely to grab attention and retain viewers.
    Returns an integer score (0-100+).
    """
    score = 0
    combined = (title + " " + body).lower()

    # 1. Dramatic keyword density (biggest factor)
    keyword_hits = sum(1 for kw in VIRAL_KEYWORDS if kw in combined)
    score += keyword_hits * 8  # Each keyword worth 8 points

    # 2. Exclamation marks signal emotional intensity
    exclamation_count = combined.count('!')
    score += min(exclamation_count * 3, 15)  # Cap at 15

    # 3. Question marks in title create curiosity gaps
    if '?' in title.lower():
        score += 10

    # 4. Short, punchy opening sentence (< 12 words) = instant hook
    sentences = re.split(r'[.!?]+', body.strip())
    if sentences and len(sentences[0].split()) < 12:
        score += 8

    # 5. Conflict density — stories with "but", "however", "then" have twists
    conflict_words = ['but', 'however', 'then', 'suddenly', 'turns out',
                      'plot twist', 'little did', 'until', 'except']
    conflict_hits = sum(1 for w in conflict_words if w in combined)
    score += conflict_hits * 5

    # 6. Direct address ("I", "my") — personal stories perform better
    if combined[:50].count(' i ') >= 1 or combined.startswith('i ') or 'my ' in combined[:30]:
        score += 5

    # 7. ALL CAPS words signal dramatic moments
    caps_words = re.findall(r'\b[A-Z]{3,}\b', title + " " + body)
    score += min(len(caps_words) * 4, 12)

    return score


def extract_hook(title, body):
    """
    Finds the most dramatic sentence in the story and moves it to the front.
    This creates a curiosity gap — the viewer HEARs the climax first, then
    wants to know the context.

    Returns: (hook_sentence, restructured_body)
    """
    sentences = re.split(r'(?<=[.!?])\s+', body.strip())

    if len(sentences) < 3:
        # Too short to restructure — just return as-is
        return title, body

    # Score each sentence for "drama"
    best_score = -1
    best_idx = 0

    for i, sentence in enumerate(sentences):
        s_score = 0
        s_lower = sentence.lower()

        # Dramatic keywords
        s_score += sum(2 for kw in VIRAL_KEYWORDS if kw in s_lower)
        # Exclamation marks
        s_score += sentence.count('!') * 3
        # Short + punchy (under 15 words)
        if len(sentence.split()) < 15:
            s_score += 3
        # Don't pick the very first sentence (it's usually setup)
        if i == 0:
            s_score -= 2
        # Prefer sentences from the middle or end (the climax)
        if i >= len(sentences) // 2:
            s_score += 2

        if s_score > best_score:
            best_score = s_score
            best_idx = i

    # If the best hook is genuinely dramatic, restructure
    if best_score >= 4 and best_idx > 0:
        hook = sentences[best_idx]
        remaining = sentences[:best_idx] + sentences[best_idx + 1:]
        restructured_body = " ".join(remaining)
        return hook, restructured_body
    else:
        # No clear hook found — use the title as the hook
        return title, body


def inject_dramatic_pauses(text):
    """
    Adds strategic commas before dramatic words to create natural TTS pauses.
    This makes the narration sound more human and builds suspense.
    """
    # Add a pause (comma) before dramatic reveal words
    pause_before = [
        'suddenly', 'but then', 'turns out', 'however', 'and then',
        'so I', 'that\'s when', 'little did', 'the next day', 'finally'
    ]
    for phrase in pause_before:
        # Only add comma if there isn't one already
        pattern = re.compile(r'(?<!,)\s+(' + re.escape(phrase) + r')', re.IGNORECASE)
        text = pattern.sub(r', \1', text)

    return text


def get_reddit_story():
    """
    Scrapes popular posts from viral subreddits using Reddit's RSS Feeds,
    scores them for viral potential, and restructures the best one with
    a hook-first format.

    Returns a tuple: (title, story_text, subreddit_name)
    """
    # We must use a descriptive bot User-Agent
    headers = {
        'User-Agent': 'python:yt_automater_bot:v3.0 (by /u/automation)'
    }

    all_valid_posts = []

    # Try multiple subreddits to build a pool of candidates
    subreddits_to_try = random.sample(SUBREDDITS, min(5, len(SUBREDDITS)))

    for subreddit in subreddits_to_try:
        timeframe = random.choice(["day", "week", "month"])

        print(f"Fetching from r/{subreddit} (Top of the {timeframe}) via RSS...")

        url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t={timeframe}"

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text
                content_elem = entry.find('atom:content', ns)

                if content_elem is not None and content_elem.text:
                    body_html = html.unescape(content_elem.text)

                    # Strip HTML tags
                    body_text = re.sub(r'<[^>]+>', ' ', body_html)
                    # Collapse multiple spaces
                    body_text = re.sub(r'\s+', ' ', body_text)
                    # Strip RSS footer
                    body_text = re.sub(
                        r'submitted by /u/\S+ \[link\] \[comments\]', '', body_text
                    ).strip()

                    body_lower = body_text.lower()
                    title_lower = title.lower()

                    # Skip boring/sensitive content
                    if any(word in body_lower for word in BORING_KEYWORDS) or \
                       any(word in title_lower for word in BORING_KEYWORDS):
                        continue

                    word_count = len(body_text.split())

                    # Target 120-155 words for 35-50 second videos (sweet spot)
                    if 120 < word_count < 160:
                        viral_score = score_story_virality(title, body_text)
                        all_valid_posts.append({
                            'title': title,
                            'body': body_text,
                            'subreddit': subreddit,
                            'score': viral_score
                        })

        except Exception as e:
            print(f"Error fetching from r/{subreddit}: {e}")

    if all_valid_posts:
        # Sort by viral score, pick from top 3 (some randomness to avoid repetition)
        all_valid_posts.sort(key=lambda x: x['score'], reverse=True)
        top_candidates = all_valid_posts[:min(3, len(all_valid_posts))]
        chosen = random.choice(top_candidates)

        print(f"\n✅ Selected story from r/{chosen['subreddit']} "
              f"(viral score: {chosen['score']})")

        final_title = clean_text(chosen['title'])
        final_body = clean_text(chosen['body'])

        # Extract the hook and restructure
        hook, restructured_body = extract_hook(final_title, final_body)

        # Inject dramatic pauses for TTS
        full_script = f"{hook}. {restructured_body}"
        full_script = inject_dramatic_pauses(full_script)

        return final_title, full_script, chosen['subreddit']

    # Fallback if ALL attempts fail
    print("⚠️ No valid posts found. Using fallback story.")
    return (
        "Why I love automation",
        "Automation is great because it does the work for you while you sleep. "
        "I built a bot that makes videos, and now I just watch it go. "
        "It's the best feeling in the world. Subscribe for more tech tips.",
        "technology"
    )


if __name__ == "__main__":
    title, body, sub = get_reddit_story()
    print(f"\nTitle: {title}")
    print(f"Subreddit: r/{sub}")
    print(f"Word count: {len(body.split())}")
    print(f"Body: {body[:200]}...")
