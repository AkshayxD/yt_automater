import os
import sys
import re
import json
import shutil
import time
import random
from datetime import datetime, timedelta

# Fix Windows console encoding for emoji in log output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from scraper import get_reddit_story, VIRAL_KEYWORDS
from audio_gen import generate_audio_and_subs
from video_gen import create_video
from youtube_api import get_authenticated_service
from uploader import upload_video
from script_writer import rewrite_story
from inspiration_writer import generate_inspiration_script
from wyr_writer import generate_wyr_script
from fake_text_writer import generate_fake_text_script
from dark_psych_writer import generate_dark_psych_script
from true_crime_writer import generate_true_crime_script
from number_facts_writer import generate_number_fact_script
from history_writer import generate_history_script
from quiz_writer import generate_quiz_script
from background_manager import pick_background_segment, record_used_segment

# --- Directories ---
VIDEOS_DIR = "videos_to_upload"
UPLOADED_DIR = "uploaded_videos"
TEMP_DIR = "temp"
ASSETS_DIR = "assets"

# --- Configuration ---
NUM_VIDEOS = int(os.environ.get("NUM_VIDEOS", "1"))  # How many videos per run
UPLOAD_COOLDOWN_MIN = 240  # Minimum cooldown between uploads (seconds)
UPLOAD_COOLDOWN_MAX = 420  # Maximum cooldown — randomized to look human
HISTORY_FILE = "upload_history.json"


def setup_directories():
    """Creates necessary directories if they don't exist."""
    for d in [VIDEOS_DIR, UPLOADED_DIR, TEMP_DIR, ASSETS_DIR]:
        os.makedirs(d, exist_ok=True)


def load_upload_history():
    """Loads the upload history to prevent duplicate stories."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"uploaded_titles": [], "videos": []}
    return {"uploaded_titles": [], "videos": []}


def save_upload_history(history):
    """Saves the upload history."""
    # Keep only the last 500 entries to prevent the file from growing forever
    history["uploaded_titles"] = history["uploaded_titles"][-500:]
    history["videos"] = history["videos"][-500:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def is_duplicate(title, history):
    """Checks if a story has already been uploaded."""
    # Normalize for comparison
    normalized = title.lower().strip()
    for prev_title in history.get("uploaded_titles", []):
        if normalized == prev_title.lower().strip():
            return True
        # Also check for high similarity (e.g., slight wording differences)
        if len(normalized) > 20 and normalized[:20] == prev_title.lower().strip()[:20]:
            return True
    return False


def generate_viral_metadata(title, body, subreddit):
    """
    Generates SEO-optimized metadata designed for maximum reach.
    
    Strategy:
    - Title: Clean, curiosity-driven, ≤50 chars, no clutter
    - Description: Hook line + exactly 5 hashtags + CTA
    - Tags: 10 max (YouTube ignores all tags if you use 60+)
    
    Returns: (short_title, description, tags)
    """
    # --- TITLE ---
    # Use the title directly (it's already the AI headline, which is punchy)
    # Just clean it up and cap the length
    short_title = title.strip()
    
    # Remove redundant quotes/formatting
    short_title = short_title.strip('"').strip("'").strip()
    
    # Cap at 50 chars (front-load keywords, no truncation mid-word)
    if len(short_title) > 50:
        short_title = short_title[:47]
        last_space = short_title.rfind(' ')
        if last_space > 25:
            short_title = short_title[:last_space]
        short_title += "..."
    
    # --- Human-like title variations (anti-fingerprinting) ---
    # Randomly vary punctuation and casing to avoid bot detection patterns
    title_variation = random.randint(0, 3)
    if title_variation == 0:
        pass  # Keep as-is
    elif title_variation == 1 and not short_title.endswith(('?', '!', '...')):
        short_title += "..."  # Trailing ellipsis for mystery
    elif title_variation == 2 and not short_title.endswith(('?', '!', '...')):
        short_title = short_title.rstrip('.')  # Clean ending
    # title_variation == 3: keep as-is (no change)

    # --- DESCRIPTION ---
    # First line = curiosity hook, then strategic hashtags, then CTA
    first_sentence = body.split('.')[0].strip() if body else ""
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:117] + "..."

    # Exactly 5 strategic hashtags (over-tagging causes YouTube to ignore all)
    # 3 broad + 2 topic-specific
    subreddit_hashtag_map = {
        "pettyrevenge": "#PettyRevenge #Karma",
        "prorevenge": "#ProRevenge #Justice",
        "nuclearrevenge": "#NuclearRevenge #Justice",
        "maliciouscompliance": "#MaliciousCompliance #Revenge",
        "confession": "#Confession #TrueStory",
        "tifu": "#TIFU #FunnyStory",
        "entitledparents": "#EntitledParents #Karen",
        "trueoffmychest": "#TrueOffMyChest #Confession",
        "amitheasshole": "#AITA #AmITheAsshole",
        "choosingbeggars": "#ChoosingBeggars #Entitled",
        "idontworkherelady": "#IDontWorkHereLady #Karen",
        "relationships": "#Relationships #Drama",
        "neighborsfromhell": "#BadNeighbors #Neighbors",
        "bestofredditorupdates": "#RedditUpdates #StoryTime",
        "weddingshaming": "#WeddingDrama #Bridezilla",
        "bridezillas": "#Bridezilla #WeddingDrama",
        "justnomil": "#MotherInLaw #FamilyDrama",
    }

    sub_tags = subreddit_hashtag_map.get(subreddit.lower(), "#RedditStories #StoryTime")

    description = (
        f"{first_sentence}\n\n"
        f"#Shorts #RedditStories {sub_tags}\n\n"
        f"Follow for daily stories! 🔔\n\n"
        f"---\n"
        f"Story from r/{subreddit}"
    )

    # --- TAGS ---
    # 10 max — focused mix of broad + niche
    base_tags = ["shorts", "reddit stories", "storytime", "reddit", "true stories"]

    body_lower = body.lower()
    topic_tags = []
    topic_map = {
        "revenge": ["revenge story", "karma"],
        "boss": ["work story", "bad boss"],
        "wedding": ["wedding drama"],
        "neighbor": ["bad neighbor"],
        "cheating": ["cheating story"],
        "parent": ["entitled parents"],
        "school": ["school story"],
        "roommate": ["roommate story"],
        "divorce": ["divorce story"],
    }

    for keyword, tags in topic_map.items():
        if keyword in body_lower:
            topic_tags.extend(tags)

    sub_name_clean = subreddit.lower().replace("_", " ")
    topic_tags.append(sub_name_clean)

    all_tags = base_tags + list(set(topic_tags))
    all_tags = all_tags[:10]  # Hard cap at 10

    return short_title, description, all_tags


def generate_inspiration_metadata(headline, script_text, philosopher):
    """
    Generates SEO-optimized metadata for Dark Stoic / Motivational shorts.
    
    Strategy:
    - Title: The AI headline as-is (already punchy and ALL CAPS)
    - Description: Quote + philosopher attribution + motivational hashtags
    - Tags: Mix of broad motivational + Stoic-specific keywords
    
    Returns: (short_title, description, tags)
    """
    # --- TITLE ---
    short_title = headline.strip().strip('"').strip("'").strip()
    if len(short_title) > 50:
        short_title = short_title[:47]
        last_space = short_title.rfind(' ')
        if last_space > 25:
            short_title = short_title[:last_space]
        short_title += "..."
    
    # --- DESCRIPTION ---
    # First meaningful sentence from the script
    first_sentence = script_text.split('.')[0].strip() if script_text else ""
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:117] + "..."
    
    # Stoic-specific hashtags (5 max — YouTube ignores excess)
    description = (
        f"{first_sentence}\n\n"
        f"#Shorts #Stoicism #DarkMotivation #MarcusAurelius #Mindset\n\n"
        f"Wisdom from {philosopher} \U0001F3DB\uFE0F\n"
        f"Follow for your daily Stoic lesson \U0001F514\n\n"
        f"---\n"
        f"#StoicWisdom #Philosophy #Motivation"
    )
    
    # --- TAGS ---
    base_tags = ["shorts", "stoicism", "motivation", "dark motivation", "mindset"]
    topic_tags = [
        "marcus aurelius", "seneca", "stoic wisdom",
        "self improvement", "philosophy", "mental strength"
    ]
    
    # Add philosopher-specific tag
    if philosopher:
        philosopher_tag = philosopher.lower()
        if philosopher_tag not in [t.lower() for t in topic_tags]:
            topic_tags.append(philosopher_tag)
    
    all_tags = base_tags + topic_tags
    all_tags = all_tags[:10]  # Hard cap at 10
    
    return short_title, description, all_tags


def generate_wyr_metadata(headline, script_text):
    """
    Generates SEO-optimized metadata for Would You Rather shorts.
    
    Returns: (short_title, description, tags)
    """
    short_title = headline.strip().strip('"').strip("'").strip()
    if len(short_title) > 50:
        short_title = short_title[:47]
        last_space = short_title.rfind(' ')
        if last_space > 25:
            short_title = short_title[:last_space]
        short_title += "..."
    
    first_sentence = script_text.split('.')[0].strip() if script_text else ""
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:117] + "..."
    
    description = (
        f"{first_sentence}\n\n"
        f"#Shorts #WouldYouRather #ThisOrThat #Quiz #Debate\n\n"
        f"Comment A or B! \U0001F447\n"
        f"Follow for daily impossible choices \U0001F514\n\n"
        f"---\n"
        f"#WYR #Questions #FunFacts"
    )
    
    base_tags = ["shorts", "would you rather", "this or that", "quiz", "debate"]
    topic_tags = ["fun questions", "impossible choices", "wyr", "comment below", "interactive"]
    all_tags = base_tags + topic_tags
    all_tags = all_tags[:10]
    
    return short_title, description, all_tags


def generate_fake_text_metadata(headline, script_text):
    """
    Generates SEO-optimized metadata for Fake Text Message shorts.
    
    Returns: (short_title, description, tags)
    """
    short_title = headline.strip().strip('"').strip("'").strip()
    if len(short_title) > 50:
        short_title = short_title[:47]
        last_space = short_title.rfind(' ')
        if last_space > 25:
            short_title = short_title[:last_space]
        short_title += "..."
    
    first_sentence = script_text.split('.')[0].strip() if script_text else ""
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:117] + "..."
    
    description = (
        f"{first_sentence}\n\n"
        f"#Shorts #TextStory #FakeTexts #Drama #StoryTime\n\n"
        f"Would you have replied? \U0001F4F1\n"
        f"Follow for daily text dramas \U0001F514\n\n"
        f"---\n"
        f"#TextMessages #Toxic #Relationships"
    )
    
    base_tags = ["shorts", "text story", "fake texts", "drama", "storytime"]
    topic_tags = ["text messages", "toxic texts", "relationships", "messages", "chat story"]
    all_tags = base_tags + topic_tags
    all_tags = all_tags[:10]
    
    return short_title, description, all_tags


def generate_dark_psych_metadata(headline, script_text, topic):
    """
    Generates SEO-optimized metadata for Dark Psychology shorts.
    
    Returns: (short_title, description, tags)
    """
    short_title = headline.strip().strip('"').strip("'").strip()
    if len(short_title) > 50:
        short_title = short_title[:47]
        last_space = short_title.rfind(' ')
        if last_space > 25:
            short_title = short_title[:last_space]
        short_title += "..."
    
    first_sentence = script_text.split('.')[0].strip() if script_text else ""
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:117] + "..."
    
    description = (
        f"{first_sentence}\n\n"
        f"#Shorts #DarkPsychology #Manipulation #Psychology #MindTricks\n\n"
        f"Save this. You'll need it. \U0001F4CC\n"
        f"Follow for daily psychology \U0001F514\n\n"
        f"---\n"
        f"Topic: {topic}\n"
        f"#PsychologyFacts #SelfDefense #Awareness"
    )
    
    base_tags = ["shorts", "dark psychology", "manipulation", "psychology", "mind tricks"]
    topic_tags = ["psychology facts", "narcissist", "self defense", "awareness", "did you know"]
    
    if topic:
        topic_tag = topic.lower().replace("the ", "").replace(" — ", " ")
        if topic_tag not in [t.lower() for t in topic_tags]:
            topic_tags.append(topic_tag)
    
    all_tags = base_tags + topic_tags
    all_tags = all_tags[:10]
    
    return short_title, description, all_tags


def generate_true_crime_metadata(headline, script_text, source_sub):
    """
    Generates SEO-optimized metadata for True Crime / Scary Story shorts.
    
    Returns: (short_title, description, tags)
    """
    short_title = headline.strip().strip('"').strip("'").strip()
    if len(short_title) > 50:
        short_title = short_title[:47]
        last_space = short_title.rfind(' ')
        if last_space > 25:
            short_title = short_title[:last_space]
        short_title += "..."
    
    first_sentence = script_text.split('.')[0].strip() if script_text else ""
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:117] + "..."
    
    description = (
        f"{first_sentence}\n\n"
        f"#Shorts #ScaryStories #Horror #TrueCrime #Creepy\n\n"
        f"Don't watch this alone... \U0001F480\n"
        f"Follow for daily horror \U0001F514\n\n"
        f"---\n"
        f"#CreepyStories #Paranormal #NightmareStories"
    )
    
    base_tags = ["shorts", "scary stories", "horror", "true crime", "creepy"]
    topic_tags = ["creepy stories", "paranormal", "nightmare", "nosleep", "haunted"]
    
    if source_sub and not source_sub.startswith("ai_"):
        sub_tag = source_sub.lower().replace("_", " ")
        topic_tags.append(sub_tag)
    
    all_tags = base_tags + topic_tags
    all_tags = all_tags[:10]

    return short_title, description, all_tags


def generate_number_facts_metadata(headline, script_text, key_number):
    """
    Generates SEO-optimized metadata for Number Facts shorts.
    """
    short_title = headline.strip().strip('"').strip("'").strip()
    if len(short_title) > 50:
        short_title = short_title[:47]
        last_space = short_title.rfind(' ')
        if last_space > 25:
            short_title = short_title[:last_space]
        short_title += "..."

    first_sentence = script_text.split('.')[0].strip() if script_text else ""
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:117] + "..."

    description = (
        f"{first_sentence}\n\n"
        f"#Shorts #NumberFacts #MindBlow #DidYouKnow #StatsFacts\n\n"
        f"Key metric: {key_number} 😲\n"
        f"Follow for daily mind-bending facts! 🔔\n\n"
        f"---\n"
        f"#MathFacts #Science #Probability #IncomprehensibleScale"
    )

    base_tags = ["shorts", "number facts", "mind blow", "did you know", "stats facts"]
    topic_tags = ["math facts", "science facts", "probability", "scale facts", "crazy math", "mind blowing"]
    all_tags = base_tags + topic_tags
    all_tags = all_tags[:10]

    return short_title, description, all_tags


def generate_history_metadata(headline, script_text, year):
    """
    Generates SEO-optimized metadata for Historical Facts shorts.
    """
    short_title = headline.strip().strip('"').strip("'").strip()
    if len(short_title) > 50:
        short_title = short_title[:47]
        last_space = short_title.rfind(' ')
        if last_space > 25:
            short_title = short_title[:last_space]
        short_title += "..."

    first_sentence = script_text.split('.')[0].strip() if script_text else ""
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:117] + "..."

    description = (
        f"{first_sentence}\n\n"
        f"#Shorts #History #HistoricalFacts #OnThisDay #HistoryStories\n\n"
        f"Year: {year} 🏛️\n"
        f"Follow for daily history lessons! 🔔\n\n"
        f"---\n"
        f"#DidYouKnow #WorldHistory #TodayInHistory #EpicMoments"
    )

    base_tags = ["shorts", "history", "historical facts", "on this day", "historytime"]
    topic_tags = [f"history {year}", "world history", "today in history", "history facts", "historical events", "did you know"]
    all_tags = base_tags + topic_tags
    all_tags = all_tags[:10]

    return short_title, description, all_tags


def create_and_upload_viral_short(youtube_client=None, history=None, voice=None, background_path=None, test_story=None):
    """
    The main pipeline: fetch story -> voice -> video -> upload.
    
    Returns:
        dict with 'success', 'title', 'video_id', 'file_path' keys
    """
    result = {'success': False, 'title': None, 'video_id': None, 'file_path': None}

    # 1. Fetch Script (with dedup check)
    max_fetch_attempts = 3
    title, body, subreddit = None, None, None

    if test_story:
        title, body, subreddit = test_story
    else:
        for attempt in range(max_fetch_attempts):
            title, body, subreddit = get_reddit_story()
            if history and is_duplicate(title, history):
                print(f"  ⚠️ Duplicate story detected: '{title[:40]}...' — retrying")
                continue
            break
        else:
            print("  ❌ Could not find a non-duplicate story after retries")
            return result

    print(f"\n  📖 Story: {title[:60]}")
    print(f"  📍 From: r/{subreddit}")
    print(f"  📏 Length: {len(body.split())} words")

    # --- AI Script Rewriting ---
    # Transform raw Reddit text into a viral narration script with punchy headline
    print("\n  🤖 AI Script Rewriting...")
    ai_headline, script_text, script_text2 = rewrite_story(title, body)
    print(f"  📰 Headline: {ai_headline}")
    
    parts = []
    if script_text2:
        parts.append({"script": script_text, "suffix": " (Part 1)", "is_part1": True})
        parts.append({"script": script_text2, "suffix": " (Part 2)", "is_part1": False})
    else:
        parts.append({"script": script_text, "suffix": "", "is_part1": True})

    results_list = []
    
    for part in parts:
        print(f"\n  ▶ Processing {part['suffix'] or 'Full Story'}...")
        
        # Put the headline back into the script so the voiceover actually speaks it!
        # Only speak the headline for Part 1 or full stories
        if part['is_part1']:
            full_spoken_text = f"{ai_headline}. {part['script']}"
        else:
            full_spoken_text = part['script']

        # Safety check on length (prevent 60s+ Shorts) — target is 100-115 words
        if len(full_spoken_text.split()) > 140:
            print("  ⚠️ Script unusually long — trimming")
            trimmed = ' '.join(full_spoken_text.split()[:120])
            
            # Find the last sentence boundary (. ! or ?)
            boundaries = [trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?')]
            last_boundary = max(boundaries)
            
            if last_boundary > int(len(trimmed) * 0.7):
                full_spoken_text = trimmed[:last_boundary + 1]
            else:
                full_spoken_text = trimmed

        # 2. Generate Audio and Word-Level Subtitles (SRT with exact timestamps)
        print("  🎤 Generating voiceover and subtitles...")
        audio_file = os.path.join(TEMP_DIR, "audio.mp3")
        subs_file = os.path.join(TEMP_DIR, "subs.srt")

        mp3_path, srt_path = generate_audio_and_subs(full_spoken_text, audio_file, subs_file, voice=voice)

        if not mp3_path or not srt_path:
            print("  ❌ Failed to generate audio. Aborting this part.")
            continue

        # 3. Assemble Video
        print("  🎥 Assembling video...")
        # TASK 6: Use AI headline for filename instead of raw Reddit title
        safe_title = "".join([c for c in ai_headline if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
        safe_title_underscored = safe_title.replace(" ", "_")[:50]
        if part['suffix']:
            safe_title_underscored += f"_Part_{part['suffix'][-2]}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_video_path = os.path.join(VIDEOS_DIR, f"{safe_title_underscored}_{timestamp}.mp4")

        # Pick a background video + segment that hasn't been used before
        # background_manager tracks all used time ranges across all background files
        if background_path and os.path.exists(background_path):
            # Manually specified background: use manager just for the start time
            bg_video = background_path
            bg_start = None  # Will be handled inside create_video (random fallback)
            print(f"  Using specified background: {bg_video}")
        else:
            # Let the manager pick the best video + segment
            bg_video, bg_start = pick_background_segment(needed_duration=50.0)  # ~45s buffer
            if bg_video is None:
                bg_video = os.path.join(ASSETS_DIR, "background_small.mp4")
                bg_start = None

        try:
            rendered_video = create_video(
                mp3_path, srt_path,
                background_path=bg_video,
                output_path=final_video_path,
                bg_start_time=bg_start
            )
            # Record the used segment so it won't be reused
            if bg_start is not None and rendered_video:
                from moviepy.editor import AudioFileClip as _AFC
                _audio_dur = _AFC(mp3_path).duration
                record_used_segment(bg_video, bg_start, bg_start + _audio_dur)
        except Exception as e:
            print(f"  ❌ Error during video generation: {e}")
            continue

        part_result = {'success': False, 'title': None, 'video_id': None, 'file_path': rendered_video}

        # 4. Generate viral metadata
        short_title, description, tags = generate_viral_metadata(ai_headline, body, subreddit)
        upload_title = short_title + part['suffix']
        print(f"  📋 Upload title: {upload_title}")

        # 5. Upload to YouTube
        if youtube_client:
            print("  📤 Uploading to YouTube...")
            try:
                video_id = upload_video(
                    youtube=youtube_client,
                    file_path=rendered_video,
                    title=upload_title,
                    description=description,
                    category_id="24",  # Entertainment
                    keywords=tags,
                    privacy_status="public"
                )

                if video_id:
                    part_result['success'] = True
                    part_result['title'] = title + part['suffix']
                    part_result['video_id'] = video_id

                    # Move to uploaded folder
                    dest_path = os.path.join(UPLOADED_DIR, os.path.basename(rendered_video))
                    shutil.move(rendered_video, dest_path)
                    print(f"  Moved video to {UPLOADED_DIR}/")

                    # PINNED COMMENT LOGIC
                    # Uses rotating comment pool for variety (prevents viewer fatigue)
                    # Part 1 = teaser for Part 2, Final part = debate/engagement bait
                    try:
                        from uploader import add_pinned_comment, get_pinned_comment
                        is_part1 = (part['suffix'] == " (Part 1)")
                        comment_text = get_pinned_comment(is_part1=is_part1)
                        
                        add_pinned_comment(youtube_client, video_id, comment_text)
                    except Exception as e:
                        print(f"  ⚠️ Could not pin comment: {e}")

            except Exception as e:
                print(f"  ❌ Failed to upload video: {e}")
                print(f"  Your video is saved at {rendered_video}")
        else:
            print(f"  ⏭️ Skipping upload (no YouTube client or upload disabled)")
            print(f"  Video saved at: {rendered_video}")
            part_result['success'] = True
            part_result['title'] = title + part['suffix']

        results_list.append(part_result)

    # Return the first part's result, or an aggregated result
    if results_list:
        return results_list[0]
    return result


def create_inspirational_short(youtube_client=None, history=None, voice=None):
    """
    Pipeline for Dark Stoic / Motivational shorts.
    
    Differences from create_and_upload_viral_short:
    - Uses inspiration_writer.py (AI-generated Stoic scripts, no Reddit scraping)
    - Picks backgrounds from assets/inspiration_bg/
    - Picks music from assets/inspiration_music/
    - Uses deeper, calmer voices at slower TTS rate
    - White text, smaller font, calmer zoom (content_type='inspiration')
    - Uploads under category 22 (People & Blogs) instead of 24 (Entertainment)
    
    Returns:
        dict with 'success', 'title', 'video_id', 'file_path' keys
    """
    result = {'success': False, 'title': None, 'video_id': None, 'file_path': None}
    
    # 1. Get recently used themes from history to avoid repetition
    used_themes = []
    if history:
        for vid in history.get('videos', [])[-30:]:
            theme = vid.get('stoic_theme')
            if theme:
                used_themes.append(theme)
    
    # 2. Generate inspiration script via Gemini AI
    print("\n  \U0001F3DB\uFE0F Generating Dark Stoic script...")
    headline, script_text, philosopher, theme_name = generate_inspiration_script(used_themes)
    
    print(f"\n  \U0001F4F0 Headline: {headline}")
    print(f"  \U0001F3DB\uFE0F Philosopher: {philosopher}")
    print(f"  \U0001F4CF Words: {len(script_text.split())}")
    
    # 3. Generate Audio (deeper voice, slower rate)
    print("  \U0001F3A4 Generating voiceover...")
    audio_file = os.path.join(TEMP_DIR, "audio.mp3")
    subs_file = os.path.join(TEMP_DIR, "subs.srt")
    
    mp3_path, srt_path = generate_audio_and_subs(
        script_text, audio_file, subs_file, 
        voice=voice, content_type="inspiration"
    )
    
    if not mp3_path or not srt_path:
        print("  \u274C Failed to generate audio. Aborting.")
        return result
    
    # 4. Pick background from inspiration-specific assets
    import glob
    insp_bg_dir = os.path.join(ASSETS_DIR, "inspiration_bg")
    insp_bg_files = glob.glob(os.path.join(insp_bg_dir, '*.mp4'))
    
    if insp_bg_files:
        bg_video = random.choice(insp_bg_files)
        print(f"  \U0001F3AC Using inspiration background: {os.path.basename(bg_video)}")
    else:
        # Fallback to regular backgrounds
        bg_video, bg_start = pick_background_segment(needed_duration=50.0)
        if bg_video is None:
            bg_video = os.path.join(ASSETS_DIR, "background_small.mp4")
        print(f"  \u26A0\uFE0F No inspiration backgrounds found, using: {os.path.basename(bg_video)}")
    
    # 5. Assemble Video (inspiration style: white text, calmer zoom)
    safe_title = "".join([c for c in headline if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    safe_title_underscored = safe_title.replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_video_path = os.path.join(VIDEOS_DIR, f"INSP_{safe_title_underscored}_{timestamp}.mp4")
    
    print("  \U0001F3A5 Assembling inspiration video...")
    try:
        rendered_video = create_video(
            mp3_path, srt_path,
            background_path=bg_video,
            output_path=final_video_path,
            bg_start_time=None,
            content_type="inspiration"
        )
    except Exception as e:
        print(f"  \u274C Error during video generation: {e}")
        return result
    
    # 6. Generate metadata
    short_title, description, tags = generate_inspiration_metadata(headline, script_text, philosopher)
    print(f"  \U0001F4CB Upload title: {short_title}")
    
    # 7. Upload to YouTube
    if youtube_client:
        print("  \U0001F4E4 Uploading to YouTube...")
        try:
            video_id = upload_video(
                youtube=youtube_client,
                file_path=rendered_video,
                title=short_title,
                description=description,
                category_id="22",  # People & Blogs (better for motivational content)
                keywords=tags,
                privacy_status="public"
            )
            
            if video_id:
                result['success'] = True
                result['title'] = headline
                result['video_id'] = video_id
                result['file_path'] = rendered_video
                result['stoic_theme'] = theme_name
                
                # Move to uploaded folder
                dest_path = os.path.join(UPLOADED_DIR, os.path.basename(rendered_video))
                shutil.move(rendered_video, dest_path)
                print(f"  Moved video to {UPLOADED_DIR}/")
                
                # Pin a Stoic-themed comment for engagement
                try:
                    from uploader import add_pinned_comment
                    stoic_comments = [
                        f"\U0001F3DB\uFE0F Which {philosopher} lesson changed YOUR life? Drop it below.",
                        "Type STRENGTH if you needed to hear this today. \U0001F4AA",
                        "Save this for when life gets hard. You'll need it. \U0001F516",
                        "The person who needs this most won't see it unless you share it. \U0001F517",
                        f"\U0001F3DB\uFE0F {philosopher} understood something most people never will. What's YOUR biggest lesson?",
                    ]
                    comment_text = random.choice(stoic_comments)
                    add_pinned_comment(youtube_client, video_id, comment_text)
                except Exception as e:
                    print(f"  \u26A0\uFE0F Could not pin comment: {e}")
        except Exception as e:
            print(f"  \u274C Failed to upload video: {e}")
            print(f"  Your video is saved at {rendered_video}")
    else:
        print(f"  \u23ED\uFE0F Skipping upload (no YouTube client)")
        print(f"  Video saved at: {rendered_video}")
        result['success'] = True
        result['title'] = headline
        result['file_path'] = rendered_video
        result['stoic_theme'] = theme_name
    
    return result


def create_wyr_short(youtube_client=None, history=None, voice=None):
    """
    Pipeline for Would You Rather shorts.
    
    Differences from other pipelines:
    - Uses wyr_writer.py (AI-generated WYR dilemmas)
    - Vibrant green text, exaggerated pop animation
    - Faster TTS rate for energetic delivery
    - Uploads under category 24 (Entertainment)
    
    Returns:
        dict with 'success', 'title', 'video_id', 'file_path' keys
    """
    result = {'success': False, 'title': None, 'video_id': None, 'file_path': None}
    
    # 1. Get recently used themes from history
    used_themes = []
    if history:
        for vid in history.get('videos', [])[-30:]:
            theme = vid.get('wyr_theme')
            if theme:
                used_themes.append(theme)
    
    # 2. Generate WYR script via Gemini AI
    print("\n  \U0001F3AF Generating Would You Rather script...")
    headline, script_text, option_a, option_b, theme_name = generate_wyr_script(used_themes)
    
    print(f"\n  \U0001F4F0 Headline: {headline}")
    print(f"  \U0001F1E6 Option A: {option_a}")
    print(f"  \U0001F1E7 Option B: {option_b}")
    print(f"  \U0001F4CF Words: {len(script_text.split())}")
    
    # 3. Generate Audio (energetic voice, faster rate)
    print("  \U0001F3A4 Generating voiceover...")
    audio_file = os.path.join(TEMP_DIR, "audio.mp3")
    subs_file = os.path.join(TEMP_DIR, "subs.srt")
    
    mp3_path, srt_path = generate_audio_and_subs(
        script_text, audio_file, subs_file,
        voice=voice, content_type="would_you_rather"
    )
    
    if not mp3_path or not srt_path:
        print("  \u274C Failed to generate audio. Aborting.")
        return result
    
    # 4. Pick background
    import glob
    wyr_bg_dir = os.path.join(ASSETS_DIR, "wyr_bg")
    wyr_bg_files = glob.glob(os.path.join(wyr_bg_dir, '*.mp4'))
    
    if wyr_bg_files:
        bg_video = random.choice(wyr_bg_files)
        print(f"  \U0001F3AC Using WYR background: {os.path.basename(bg_video)}")
    else:
        bg_video, bg_start = pick_background_segment(needed_duration=50.0)
        if bg_video is None:
            bg_video = os.path.join(ASSETS_DIR, "background_small.mp4")
        print(f"  \u26A0\uFE0F No WYR backgrounds found, using: {os.path.basename(bg_video)}")
    
    # 5. Assemble Video (WYR style: green text, exaggerated pop)
    safe_title = "".join([c for c in headline if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    safe_title_underscored = safe_title.replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_video_path = os.path.join(VIDEOS_DIR, f"WYR_{safe_title_underscored}_{timestamp}.mp4")
    
    print("  \U0001F3A5 Assembling WYR video...")
    try:
        rendered_video = create_video(
            mp3_path, srt_path,
            background_path=bg_video,
            output_path=final_video_path,
            bg_start_time=None,
            content_type="would_you_rather"
        )
    except Exception as e:
        print(f"  \u274C Error during video generation: {e}")
        return result
    
    # 6. Generate metadata
    short_title, description, tags = generate_wyr_metadata(headline, script_text)
    print(f"  \U0001F4CB Upload title: {short_title}")
    
    # 7. Upload to YouTube
    if youtube_client:
        print("  \U0001F4E4 Uploading to YouTube...")
        try:
            video_id = upload_video(
                youtube=youtube_client,
                file_path=rendered_video,
                title=short_title,
                description=description,
                category_id="24",  # Entertainment
                keywords=tags,
                privacy_status="public"
            )
            
            if video_id:
                result['success'] = True
                result['title'] = headline
                result['video_id'] = video_id
                result['file_path'] = rendered_video
                result['wyr_theme'] = theme_name
                
                dest_path = os.path.join(UPLOADED_DIR, os.path.basename(rendered_video))
                shutil.move(rendered_video, dest_path)
                print(f"  Moved video to {UPLOADED_DIR}/")
                
                # Pin a WYR-themed comment for engagement
                try:
                    from uploader import add_pinned_comment
                    wyr_comments = [
                        f"I went with {option_a}. Fight me in the comments \U0001F447",
                        f"Comment A for {option_a} or B for {option_b} \u2014 no middle ground!",
                        "This one splits EVERYONE. Which side are you on? \U0001F447",
                        f"Type 1 for {option_a} or 2 for {option_b}. I need to know \U0001F914",
                        "Send this to a friend and see if they pick the same one \U0001F517",
                    ]
                    comment_text = random.choice(wyr_comments)
                    add_pinned_comment(youtube_client, video_id, comment_text)
                except Exception as e:
                    print(f"  \u26A0\uFE0F Could not pin comment: {e}")
        except Exception as e:
            print(f"  \u274C Failed to upload video: {e}")
            print(f"  Your video is saved at {rendered_video}")
    else:
        print(f"  \u23ED\uFE0F Skipping upload (no YouTube client)")
        print(f"  Video saved at: {rendered_video}")
        result['success'] = True
        result['title'] = headline
        result['file_path'] = rendered_video
        result['wyr_theme'] = theme_name
    
    return result


def create_fake_text_short(youtube_client=None, history=None, voice=None):
    """
    Pipeline for Fake Text Message shorts.
    
    Differences from other pipelines:
    - Uses fake_text_writer.py (AI-generated dramatic chat conversations)
    - Light gray narration text with standard subtitles
    - Conversational TTS voice at normal rate
    - Uploads under category 24 (Entertainment)
    
    Returns:
        dict with 'success', 'title', 'video_id', 'file_path' keys
    """
    result = {'success': False, 'title': None, 'video_id': None, 'file_path': None}
    
    # 1. Get recently used themes from history
    used_themes = []
    if history:
        for vid in history.get('videos', [])[-30:]:
            theme = vid.get('ft_theme')
            if theme:
                used_themes.append(theme)
    
    # 2. Generate Fake Text script via Gemini AI
    print("\n  \U0001F4F1 Generating Fake Text Message script...")
    headline, script_text, messages, theme_name = generate_fake_text_script(used_themes)
    
    print(f"\n  \U0001F4F0 Headline: {headline}")
    print(f"  \U0001F4AC Messages: {len(messages)}")
    print(f"  \U0001F4CF Narration words: {len(script_text.split())}")
    
    # 3. Generate Audio (conversational voice)
    print("  \U0001F3A4 Generating voiceover...")
    audio_file = os.path.join(TEMP_DIR, "audio.mp3")
    subs_file = os.path.join(TEMP_DIR, "subs.srt")
    
    mp3_path, srt_path = generate_audio_and_subs(
        script_text, audio_file, subs_file,
        voice=voice, content_type="fake_text"
    )
    
    if not mp3_path or not srt_path:
        print("  \u274C Failed to generate audio. Aborting.")
        return result
    
    # 4. Pick background
    import glob
    ft_bg_dir = os.path.join(ASSETS_DIR, "fake_text_bg")
    ft_bg_files = glob.glob(os.path.join(ft_bg_dir, '*.mp4'))
    
    if ft_bg_files:
        bg_video = random.choice(ft_bg_files)
        print(f"  \U0001F3AC Using Fake Text background: {os.path.basename(bg_video)}")
    else:
        bg_video, bg_start = pick_background_segment(needed_duration=50.0)
        if bg_video is None:
            bg_video = os.path.join(ASSETS_DIR, "background_small.mp4")
        print(f"  \u26A0\uFE0F No Fake Text backgrounds found, using: {os.path.basename(bg_video)}")
    
    # 5. Assemble Video (fake text style)
    safe_title = "".join([c for c in headline if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    safe_title_underscored = safe_title.replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_video_path = os.path.join(VIDEOS_DIR, f"TXT_{safe_title_underscored}_{timestamp}.mp4")
    
    print("  \U0001F3A5 Assembling Fake Text video...")
    try:
        rendered_video = create_video(
            mp3_path, srt_path,
            background_path=bg_video,
            output_path=final_video_path,
            bg_start_time=None,
            content_type="fake_text",
            messages=messages
        )
    except Exception as e:
        print(f"  \u274C Error during video generation: {e}")
        return result
    
    # 6. Generate metadata
    short_title, description, tags = generate_fake_text_metadata(headline, script_text)
    print(f"  \U0001F4CB Upload title: {short_title}")
    
    # 7. Upload to YouTube
    if youtube_client:
        print("  \U0001F4E4 Uploading to YouTube...")
        try:
            video_id = upload_video(
                youtube=youtube_client,
                file_path=rendered_video,
                title=short_title,
                description=description,
                category_id="24",  # Entertainment
                keywords=tags,
                privacy_status="public"
            )
            
            if video_id:
                result['success'] = True
                result['title'] = headline
                result['video_id'] = video_id
                result['file_path'] = rendered_video
                result['ft_theme'] = theme_name
                
                dest_path = os.path.join(UPLOADED_DIR, os.path.basename(rendered_video))
                shutil.move(rendered_video, dest_path)
                print(f"  Moved video to {UPLOADED_DIR}/")
                
                try:
                    from uploader import add_pinned_comment
                    ft_comments = [
                        "Would YOU have responded? Comment BLOCK or REPLY \U0001F447",
                        "The AUDACITY. What would your reply be? Drop it below \U0001F447",
                        "I need to know \u2014 who was wrong here? Comment below \u2B07\uFE0F",
                        "Screenshot this and send it to your friend who would FLIP \U0001F4F8",
                        "Has something like this ever happened to YOU? Share your story \U0001F447",
                    ]
                    comment_text = random.choice(ft_comments)
                    add_pinned_comment(youtube_client, video_id, comment_text)
                except Exception as e:
                    print(f"  \u26A0\uFE0F Could not pin comment: {e}")
        except Exception as e:
            print(f"  \u274C Failed to upload video: {e}")
            print(f"  Your video is saved at {rendered_video}")
    else:
        print(f"  \u23ED\uFE0F Skipping upload (no YouTube client)")
        print(f"  Video saved at: {rendered_video}")
        result['success'] = True
        result['title'] = headline
        result['file_path'] = rendered_video
        result['ft_theme'] = theme_name
    
    return result


def create_dark_psych_short(youtube_client=None, history=None, voice=None):
    """
    Pipeline for Dark Psychology / Did You Know shorts.
    
    Differences from other pipelines:
    - Uses dark_psych_writer.py (AI-generated psychology facts)
    - Red accent text, authoritative style
    - Slower TTS rate for gravitas
    - Uploads under category 27 (Education)
    
    Returns:
        dict with 'success', 'title', 'video_id', 'file_path' keys
    """
    result = {'success': False, 'title': None, 'video_id': None, 'file_path': None}
    
    # 1. Get recently used topics from history
    used_topics = []
    if history:
        for vid in history.get('videos', [])[-30:]:
            topic = vid.get('psych_topic')
            if topic:
                used_topics.append(topic)
    
    # 2. Generate Dark Psychology script via Gemini AI
    print("\n  \U0001F9E0 Generating Dark Psychology script...")
    headline, script_text, topic_returned, topic_name = generate_dark_psych_script(used_topics)
    
    print(f"\n  \U0001F4F0 Headline: {headline}")
    print(f"  \U0001F9E0 Topic: {topic_returned}")
    print(f"  \U0001F4CF Words: {len(script_text.split())}")
    
    # 3. Generate Audio (deep authoritative voice)
    print("  \U0001F3A4 Generating voiceover...")
    audio_file = os.path.join(TEMP_DIR, "audio.mp3")
    subs_file = os.path.join(TEMP_DIR, "subs.srt")
    
    mp3_path, srt_path = generate_audio_and_subs(
        script_text, audio_file, subs_file,
        voice=voice, content_type="dark_psychology"
    )
    
    if not mp3_path or not srt_path:
        print("  \u274C Failed to generate audio. Aborting.")
        return result
    
    # 4. Pick background
    import glob
    dp_bg_dir = os.path.join(ASSETS_DIR, "dark_psych_bg")
    dp_bg_files = glob.glob(os.path.join(dp_bg_dir, '*.mp4'))
    
    if dp_bg_files:
        bg_video = random.choice(dp_bg_files)
        print(f"  \U0001F3AC Using Dark Psychology background: {os.path.basename(bg_video)}")
    else:
        bg_video, bg_start = pick_background_segment(needed_duration=50.0)
        if bg_video is None:
            bg_video = os.path.join(ASSETS_DIR, "background_small.mp4")
        print(f"  \u26A0\uFE0F No Dark Psychology backgrounds found, using: {os.path.basename(bg_video)}")
    
    # 5. Assemble Video (dark psychology style: red text, authoritative)
    safe_title = "".join([c for c in headline if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    safe_title_underscored = safe_title.replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_video_path = os.path.join(VIDEOS_DIR, f"PSYCH_{safe_title_underscored}_{timestamp}.mp4")
    
    print("  \U0001F3A5 Assembling Dark Psychology video...")
    try:
        rendered_video = create_video(
            mp3_path, srt_path,
            background_path=bg_video,
            output_path=final_video_path,
            bg_start_time=None,
            content_type="dark_psychology"
        )
    except Exception as e:
        print(f"  \u274C Error during video generation: {e}")
        return result
    
    # 6. Generate metadata
    short_title, description, tags = generate_dark_psych_metadata(headline, script_text, topic_returned)
    print(f"  \U0001F4CB Upload title: {short_title}")
    
    # 7. Upload to YouTube
    if youtube_client:
        print("  \U0001F4E4 Uploading to YouTube...")
        try:
            video_id = upload_video(
                youtube=youtube_client,
                file_path=rendered_video,
                title=short_title,
                description=description,
                category_id="27",  # Education
                keywords=tags,
                privacy_status="public"
            )
            
            if video_id:
                result['success'] = True
                result['title'] = headline
                result['video_id'] = video_id
                result['file_path'] = rendered_video
                result['psych_topic'] = topic_name
                
                dest_path = os.path.join(UPLOADED_DIR, os.path.basename(rendered_video))
                shutil.move(rendered_video, dest_path)
                print(f"  Moved video to {UPLOADED_DIR}/")
                
                try:
                    from uploader import add_pinned_comment
                    psych_comments = [
                        f"\U0001F9E0 Have you ever experienced {topic_returned}? Share your story below.",
                        "Save this for when someone tries to manipulate you \U0001F4CC",
                        "Tag someone who NEEDS to see this \U0001F517",
                        "Comment YES if you've seen someone do this to you \U0001F447",
                        "The scariest part? Most people never realize it's happening to them.",
                    ]
                    comment_text = random.choice(psych_comments)
                    add_pinned_comment(youtube_client, video_id, comment_text)
                except Exception as e:
                    print(f"  \u26A0\uFE0F Could not pin comment: {e}")
        except Exception as e:
            print(f"  \u274C Failed to upload video: {e}")
            print(f"  Your video is saved at {rendered_video}")
    else:
        print(f"  \u23ED\uFE0F Skipping upload (no YouTube client)")
        print(f"  Video saved at: {rendered_video}")
        result['success'] = True
        result['title'] = headline
        result['file_path'] = rendered_video
        result['psych_topic'] = topic_name
    
    return result


def create_true_crime_short(youtube_client=None, history=None, voice=None):
    """
    Pipeline for True Crime / Scary Story shorts.
    
    Differences from other pipelines:
    - Uses true_crime_writer.py (Reddit horror subs + AI-generated horror)
    - Pale gray text, minimal animation, static dread
    - Slow eerie TTS voice
    - Uploads under category 24 (Entertainment)
    
    Returns:
        dict with 'success', 'title', 'video_id', 'file_path' keys
    """
    result = {'success': False, 'title': None, 'video_id': None, 'file_path': None}
    
    # 1. Get recently used topics from history
    used_topics = []
    if history:
        for vid in history.get('videos', [])[-30:]:
            topic = vid.get('horror_topic')
            if topic:
                used_topics.append(topic)
    
    # 2. Generate True Crime script (scrape Reddit or AI-generate)
    print("\n  \U0001F480 Generating True Crime / Scary Story script...")
    headline, script_text, source_sub, theme_name = generate_true_crime_script(used_topics)
    
    print(f"\n  \U0001F4F0 Headline: {headline}")
    print(f"  \U0001F47B Source: {source_sub}")
    print(f"  \U0001F4CF Words: {len(script_text.split())}")
    
    # 3. Generate Audio (eerie voice, slow rate)
    print("  \U0001F3A4 Generating voiceover...")
    audio_file = os.path.join(TEMP_DIR, "audio.mp3")
    subs_file = os.path.join(TEMP_DIR, "subs.srt")
    
    mp3_path, srt_path = generate_audio_and_subs(
        script_text, audio_file, subs_file,
        voice=voice, content_type="true_crime"
    )
    
    if not mp3_path or not srt_path:
        print("  \u274C Failed to generate audio. Aborting.")
        return result
    
    # 4. Pick background
    import glob
    tc_bg_dir = os.path.join(ASSETS_DIR, "true_crime_bg")
    tc_bg_files = glob.glob(os.path.join(tc_bg_dir, '*.mp4'))
    
    if tc_bg_files:
        bg_video = random.choice(tc_bg_files)
        print(f"  \U0001F3AC Using True Crime background: {os.path.basename(bg_video)}")
    else:
        bg_video, bg_start = pick_background_segment(needed_duration=50.0)
        if bg_video is None:
            bg_video = os.path.join(ASSETS_DIR, "background_small.mp4")
        print(f"  \u26A0\uFE0F No True Crime backgrounds found, using: {os.path.basename(bg_video)}")
    
    # 5. Assemble Video (true crime style: pale gray, minimal animation)
    safe_title = "".join([c for c in headline if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    safe_title_underscored = safe_title.replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_video_path = os.path.join(VIDEOS_DIR, f"HORROR_{safe_title_underscored}_{timestamp}.mp4")
    
    print("  \U0001F3A5 Assembling True Crime video...")
    try:
        rendered_video = create_video(
            mp3_path, srt_path,
            background_path=bg_video,
            output_path=final_video_path,
            bg_start_time=None,
            content_type="true_crime"
        )
    except Exception as e:
        print(f"  \u274C Error during video generation: {e}")
        return result
    
    # 6. Generate metadata
    short_title, description, tags = generate_true_crime_metadata(headline, script_text, source_sub)
    print(f"  \U0001F4CB Upload title: {short_title}")
    
    # 7. Upload to YouTube
    if youtube_client:
        print("  \U0001F4E4 Uploading to YouTube...")
        try:
            video_id = upload_video(
                youtube=youtube_client,
                file_path=rendered_video,
                title=short_title,
                description=description,
                category_id="24",  # Entertainment
                keywords=tags,
                privacy_status="public"
            )
            
            if video_id:
                result['success'] = True
                result['title'] = headline
                result['video_id'] = video_id
                result['file_path'] = rendered_video
                result['horror_topic'] = theme_name
                
                dest_path = os.path.join(UPLOADED_DIR, os.path.basename(rendered_video))
                shutil.move(rendered_video, dest_path)
                print(f"  Moved video to {UPLOADED_DIR}/")
                
                try:
                    from uploader import add_pinned_comment
                    horror_comments = [
                        "Don't read these comments at night... \U0001F480 Has anything like this happened to YOU?",
                        "I still can't sleep after writing this one. What's YOUR scariest experience? \U0001F447",
                        "Type SCARED if this gave you chills \U0001F631",
                        "Watch this again. You missed something the first time... \U0001F440",
                        "The scariest part? This could happen to anyone. Even you. \U0001F47B",
                    ]
                    comment_text = random.choice(horror_comments)
                    add_pinned_comment(youtube_client, video_id, comment_text)
                except Exception as e:
                    print(f"  \u26A0\uFE0F Could not pin comment: {e}")
        except Exception as e:
            print(f"  \u274C Failed to upload video: {e}")
            print(f"  Your video is saved at {rendered_video}")
    else:
        print(f"  \u23ED\uFE0F Skipping upload (no YouTube client)")
        print(f"  Video saved at: {rendered_video}")
        result['success'] = True
        result['title'] = headline
        result['file_path'] = rendered_video
        result['horror_topic'] = theme_name
    
    return result


def create_number_facts_short(youtube_client=None, history=None, voice=None):
    """
    Pipeline for Number Facts shorts.

    Returns:
        dict with 'success', 'title', 'video_id', 'file_path' keys
    """
    result = {'success': False, 'title': None, 'video_id': None, 'file_path': None}

    # 1. Get recently used themes
    used_themes = []
    if history:
        for vid in history.get('videos', [])[-30:]:
            theme = vid.get('number_theme')
            if theme:
                used_themes.append(theme)

    # 2. Generate number fact script
    print("\n  🔢 Generating Number Fact...")
    headline, script_text, key_number, theme_name = generate_number_fact_script(used_themes)

    print(f"\n  📰 Headline: {headline}")
    print(f"  🔢 Key Number: {key_number}")
    print(f"  📝 Words: {len(script_text.split())}")

    # 3. Generate Audio
    print("  🎤 Generating voiceover...")
    audio_file = os.path.join(TEMP_DIR, "audio.mp3")
    subs_file = os.path.join(TEMP_DIR, "subs.srt")

    mp3_path, srt_path = generate_audio_and_subs(
        script_text, audio_file, subs_file,
        voice=voice, content_type="story"
    )

    if not mp3_path or not srt_path:
        print("  ❌ Failed to generate audio. Aborting.")
        return result

    # 4. Pick space/galaxy background
    import glob
    nf_bg_dir = os.path.join(ASSETS_DIR, "number_facts_bg")
    nf_bg_files = glob.glob(os.path.join(nf_bg_dir, '*.mp4'))

    if nf_bg_files:
        bg_video = random.choice(nf_bg_files)
        print(f"  🎬 Using Number Facts background: {os.path.basename(bg_video)}")
    else:
        bg_video, bg_start = pick_background_segment(needed_duration=30.0)
        if bg_video is None:
            bg_video = os.path.join(ASSETS_DIR, "background_small.mp4")
        print(f"  ⚠️ No Number Facts backgrounds found, using: {os.path.basename(bg_video)}")

    # 5. Assemble Video
    safe_title = "".join([c for c in headline if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    safe_title_underscored = safe_title.replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_video_path = os.path.join(VIDEOS_DIR, f"NUM_{safe_title_underscored}_{timestamp}.mp4")

    print("  🎥 Assembling Number Facts video...")
    try:
        rendered_video = create_video(
            mp3_path, srt_path,
            background_path=bg_video,
            output_path=final_video_path,
            bg_start_time=None,
            content_type="story"
        )
    except Exception as e:
        print(f"  ❌ Error during video generation: {e}")
        return result

    # 6. Generate metadata
    short_title, description, tags = generate_number_facts_metadata(headline, script_text, key_number)
    print(f"  📋 Upload title: {short_title}")

    # 7. Upload to YouTube
    if youtube_client:
        print("  📤 Uploading to YouTube...")
        try:
            video_id = upload_video(
                youtube=youtube_client,
                file_path=rendered_video,
                title=short_title,
                description=description,
                category_id="27",
                keywords=tags,
                privacy_status="public"
            )

            if video_id:
                result['success'] = True
                result['title'] = headline
                result['video_id'] = video_id
                result['file_path'] = rendered_video
                result['number_theme'] = theme_name

                dest_path = os.path.join(UPLOADED_DIR, os.path.basename(rendered_video))
                shutil.move(rendered_video, dest_path)
                print(f"  Moved video to {UPLOADED_DIR}/")

                try:
                    from uploader import add_pinned_comment
                    nf_comments = [
                        f"Drop a 🤯 if this broke your brain. The math is real.",
                        "Your brain physically cannot comprehend this scale. Try anyway. 🧠",
                        f"Fun fact: {key_number} is just the beginning. Want more? Hit follow.",
                        "Save this for the next time someone says 'infinity isn't that big' 📌",
                        "Comment MINDBLOWN if you had to read this twice 🤯",
                    ]
                    comment_text = random.choice(nf_comments)
                    add_pinned_comment(youtube_client, video_id, comment_text)
                except Exception as e:
                    print(f"  ⚠️ Could not pin comment: {e}")
        except Exception as e:
            print(f"  ❌ Failed to upload video: {e}")
            print(f"  Your video is saved at {rendered_video}")
    else:
        print(f"  ⏭️ Skipping upload (no YouTube client)")
        print(f"  Video saved at: {rendered_video}")
        result['success'] = True
        result['title'] = headline
        result['file_path'] = rendered_video
        result['number_theme'] = theme_name

    return result


def create_history_short(youtube_client=None, history=None, voice=None):
    """
    Pipeline for Historical "On This Day" shorts.

    Returns:
        dict with 'success', 'title', 'video_id', 'file_path' keys
    """
    result = {'success': False, 'title': None, 'video_id': None, 'file_path': None}

    # 1. Get recently used themes
    used_themes = []
    if history:
        for vid in history.get('videos', [])[-30:]:
            theme = vid.get('history_theme')
            if theme:
                used_themes.append(theme)

    # 2. Generate history script (scrapes Wikipedia)
    print("\n  🏛️ Generating Historical Fact...")
    headline, script_text, image_path, year, theme_id = generate_history_script(used_themes)

    print(f"\n  📰 Headline: {headline}")
    print(f"  📅 Year: {year}")
    print(f"  📝 Words: {len(script_text.split())}")
    if image_path:
        print(f"  📸 Image: {image_path}")

    # 3. Generate Audio
    print("  🎤 Generating voiceover...")
    audio_file = os.path.join(TEMP_DIR, "audio.mp3")
    subs_file = os.path.join(TEMP_DIR, "subs.srt")

    mp3_path, srt_path = generate_audio_and_subs(
        script_text, audio_file, subs_file,
        voice=voice, content_type="story"
    )

    if not mp3_path or not srt_path:
        print("  ❌ Failed to generate audio. Aborting.")
        return result

    # 4. Use historical image as background if available, else pick from pool
    if image_path and os.path.exists(image_path):
        bg_video = image_path
        print(f"  🎬 Using historical image: {os.path.basename(bg_video)}")
    else:
        import glob
        hist_bg_dir = os.path.join(ASSETS_DIR, "history_bg")
        hist_bg_files = glob.glob(os.path.join(hist_bg_dir, '*.mp4'))

        if hist_bg_files:
            bg_video = random.choice(hist_bg_files)
            print(f"  🎬 Using history background: {os.path.basename(bg_video)}")
        else:
            bg_video, bg_start = pick_background_segment(needed_duration=50.0)
            if bg_video is None:
                bg_video = os.path.join(ASSETS_DIR, "background_small.mp4")
            print(f"  ⚠️ No history backgrounds found, using: {os.path.basename(bg_video)}")

    # 5. Assemble Video
    safe_title = "".join([c for c in headline if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    safe_title_underscored = safe_title.replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_video_path = os.path.join(VIDEOS_DIR, f"HIST_{safe_title_underscored}_{timestamp}.mp4")

    print("  🎥 Assembling History video...")
    try:
        rendered_video = create_video(
            mp3_path, srt_path,
            background_path=bg_video,
            output_path=final_video_path,
            bg_start_time=None,
            content_type="story"
        )
    except Exception as e:
        print(f"  ❌ Error during video generation: {e}")
        return result

    # 6. Generate metadata
    short_title, description, tags = generate_history_metadata(headline, script_text, year)
    print(f"  📋 Upload title: {short_title}")

    # 7. Upload to YouTube
    if youtube_client:
        print("  📤 Uploading to YouTube...")
        try:
            video_id = upload_video(
                youtube=youtube_client,
                file_path=rendered_video,
                title=short_title,
                description=description,
                category_id="27",
                keywords=tags,
                privacy_status="public"
            )

            if video_id:
                result['success'] = True
                result['title'] = headline
                result['video_id'] = video_id
                result['file_path'] = rendered_video
                result['history_theme'] = theme_id

                dest_path = os.path.join(UPLOADED_DIR, os.path.basename(rendered_video))
                shutil.move(rendered_video, dest_path)
                print(f"  Moved video to {UPLOADED_DIR}/")

                try:
                    from uploader import add_pinned_comment
                    hist_comments = [
                        f"On this day in {year}, history changed forever. What year are YOU from? Drop it below 👇",
                        f"Rate this historical moment 1-10 in the comments 🏛️",
                        "This is why history class matters. Follow for daily lessons 📚",
                        f"Would you have survived {year}? Be honest in the comments 💀",
                        "Share this with someone who loves history 🔗",
                    ]
                    comment_text = random.choice(hist_comments)
                    add_pinned_comment(youtube_client, video_id, comment_text)
                except Exception as e:
                    print(f"  ⚠️ Could not pin comment: {e}")
        except Exception as e:
            print(f"  ❌ Failed to upload video: {e}")
            print(f"  Your video is saved at {rendered_video}")
    else:
        print(f"  ⏭️ Skipping upload (no YouTube client)")
        print(f"  Video saved at: {rendered_video}")
        result['success'] = True
        result['title'] = headline
        result['file_path'] = rendered_video
        result['history_theme'] = theme_id

    return result


def create_quiz_short(youtube_client=None, history=None, voice=None):
    """
    Pipeline for Interactive Quiz shorts.
    """
    result = {'success': False, 'title': None, 'video_id': None, 'file_path': None}

    used_themes = []
    if history:
        for vid in history.get('videos', [])[-30:]:
            theme = vid.get('quiz_theme')
            if theme:
                used_themes.append(theme)

    print("\n  ❓ Generating Quiz...")
    headline, script_text, theme_name, answer_keyword, visual_prompt = generate_quiz_script(used_themes)
    print(f"\n  📰 Headline: {headline}")
    print(f"  📝 Words: {len(script_text.split())}")

    popup_image_path = None
    if visual_prompt and answer_keyword:
        import urllib.parse
        import urllib.request
        print(f"  🎨 Generating AI image for answer: {answer_keyword}")
        safe_prompt = urllib.parse.quote(visual_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1080&height=1920"
        popup_image_path = os.path.join(TEMP_DIR, "quiz_visual.jpg")
        try:
            req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(popup_image_path, 'wb') as f:
                    f.write(response.read())
            print("  ✅ AI image downloaded.")
        except Exception as e:
            print(f"  ❌ Failed to download AI image: {e}")
            popup_image_path = None

    print("  🎤 Generating voiceover...")
    audio_file = os.path.join(TEMP_DIR, "audio.mp3")
    subs_file = os.path.join(TEMP_DIR, "subs.srt")

    mp3_path, srt_path = generate_audio_and_subs(
        script_text, audio_file, subs_file,
        voice=voice, content_type="quiz"
    )

    if not mp3_path or not srt_path:
        print("  ❌ Failed to generate audio. Aborting.")
        return result

    import glob
    quiz_bg_dir = os.path.join(ASSETS_DIR, "quiz_bg")
    quiz_bg_files = glob.glob(os.path.join(quiz_bg_dir, '*.mp4'))
    
    if quiz_bg_files:
        bg_video = random.choice(quiz_bg_files)
        print(f"  🎬 Using Quiz background: {os.path.basename(bg_video)}")
    else:
        bg_video, bg_start = pick_background_segment(needed_duration=30.0)
        if bg_video is None:
            bg_video = os.path.join(ASSETS_DIR, "background_small.mp4")

    safe_title = "".join([c for c in headline if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    safe_title_underscored = safe_title.replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_video_path = os.path.join(VIDEOS_DIR, f"QUIZ_{safe_title_underscored}_{timestamp}.mp4")

    print("  🎥 Assembling Quiz video...")
    try:
        rendered_video = create_video(
            mp3_path, srt_path,
            background_path=bg_video,
            output_path=final_video_path,
            bg_start_time=None,
            content_type="quiz",
            popup_image_path=popup_image_path,
            popup_trigger_word=answer_keyword
        )
    except Exception as e:
        print(f"  ❌ Error during video generation: {e}")
        return result

    short_title = headline
    description = f"{headline}\n\n#Shorts #Trivia #Quiz #Game\n\nDid you get it right?"
    tags = ["shorts", "trivia", "quiz", "game", "challenge", "brain teaser"]

    if youtube_client:
        print("  📤 Uploading to YouTube...")
        try:
            video_id = upload_video(
                youtube=youtube_client,
                file_path=rendered_video,
                title=short_title,
                description=description,
                category_id="24",
                keywords=tags,
                privacy_status="public"
            )

            if video_id:
                result['success'] = True
                result['title'] = headline
                result['video_id'] = video_id
                result['file_path'] = rendered_video
                result['quiz_theme'] = theme_name

                dest_path = os.path.join(UPLOADED_DIR, os.path.basename(rendered_video))
                shutil.move(rendered_video, dest_path)
        except Exception as e:
            print(f"  ❌ Failed to upload video: {e}")
    else:
        print(f"  ⏭️ Skipping upload (no YouTube client)")
        result['success'] = True
        result['title'] = headline
        result['file_path'] = rendered_video
        result['quiz_theme'] = theme_name

    return result


def run_pipeline():
    """
    Main entry point: generates and uploads multiple viral shorts.
    Supports command-line options for easy compilation and customization.
    """
    setup_directories()

    import argparse
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation Bot")
    parser.add_argument("-n", "--num", type=int, default=int(os.environ.get("NUM_VIDEOS", "1")), 
                        help="Number of videos to generate (default: 1)")
    parser.add_argument("--no-upload", action="store_true", 
                        help="Disable upload to YouTube, only generate files locally")
    parser.add_argument("-k", "--gemini-key", type=str, default=os.environ.get("GEMINI_API_KEY", ""), 
                        help="Google Gemini API Key for script rewriting")
    parser.add_argument("-v", "--voice", type=str, default=None, 
                        help="Force a specific TTS voice (e.g. en-GB-RyanNeural)")
    parser.add_argument("-b", "--background", type=str, default=None, 
                        help="Path to specific background video file")
    parser.add_argument("-w", "--words-per-chunk", type=int, default=2, 
                        help="Number of words per subtitle chunk (default: 2)")
    parser.add_argument("-c", "--cooldown", type=int, default=0, 
                        help="Override cooldown seconds between uploads (default: random 240-420)")
    parser.add_argument("--test-caption", action="store_true",
                        help="Generate a single test frame to verify caption styling, then exit")
    parser.add_argument("--test-video", action="store_true",
                        help="Generate a test video locally from a high-drama sample story to verify style, scripts, and voiceover.")
    parser.add_argument("--test-story-file", type=str, default=None,
                        help="Path to a text file containing a custom raw Reddit story (first line = title, rest = body) for test generation.")
    parser.add_argument("--schedule", type=str, choices=["morning", "afternoon", "evening"], default=None,
                        help="Wait until target time before uploading (morning=10AM, afternoon=2PM, evening=7PM)")
    parser.add_argument("--content-type", type=str, choices=["story", "inspiration", "would_you_rather", "fake_text", "dark_psychology", "true_crime", "number_facts", "history", "quiz"], default="story",
                        help="Content type to generate")

    args, unknown = parser.parse_known_args()

    # Set Gemini Key if passed
    if args.gemini_key:
        os.environ["GEMINI_API_KEY"] = args.gemini_key
        import script_writer
        script_writer.GEMINI_API_KEY = args.gemini_key

    # Override words per chunk if specified
    if args.words_per_chunk != 2:
        import video_gen
        video_gen.WORDS_PER_CHUNK = args.words_per_chunk
        print(f"🔧 Overriding words per chunk to: {args.words_per_chunk}")

    # --- Test Caption Mode ---
    # Generates a single frame with the caption style for quick visual QA
    if args.test_caption:
        print("\n🧪 TEST CAPTION MODE")
        print("Generating a test frame to verify caption styling...\n")
        try:
            from video_gen import (
                TextClip, CompositeVideoClip, ColorClip,
                FONT_NAME, ACTIVE_COLOR, STROKE_COLOR, STROKE_WIDTH,
                ACTIVE_FONT_SIZE, VIDEO_WIDTH, VIDEO_HEIGHT
            )
            # Create a dark background
            bg = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(30, 30, 40))
            bg = bg.set_duration(1)
            
            # Create test text with the caption style
            test_text = "KARMA"
            stroke = TextClip(test_text, fontsize=ACTIVE_FONT_SIZE,
                             color='black', font=FONT_NAME,
                             stroke_color='black', stroke_width=STROKE_WIDTH,
                             method='label', align='center')
            txt = TextClip(test_text, fontsize=ACTIVE_FONT_SIZE,
                          color=ACTIVE_COLOR, font=FONT_NAME,
                          method='label', align='center')
            
            y_pos = int(VIDEO_HEIGHT * 0.55)
            stroke = stroke.set_position(('center', y_pos)).set_duration(1)
            txt = txt.set_position(('center', y_pos)).set_duration(1)
            
            # Composite and save (bar -> stroke -> text)
            frame = CompositeVideoClip([bg, stroke, txt], size=(VIDEO_WIDTH, VIDEO_HEIGHT))
            output = os.path.join(TEMP_DIR, "test_caption.png")
            os.makedirs(TEMP_DIR, exist_ok=True)
            frame.save_frame(output, t=0)
            frame.close()
            
            print(f"✅ Test caption saved to: {os.path.abspath(output)}")
            print(f"   Color: {ACTIVE_COLOR}")
            print(f"   Font: {FONT_NAME}")
            print(f"   Size: {ACTIVE_FONT_SIZE}px | Stroke: {STROKE_WIDTH}px")
            print("\nOpen the PNG file to verify the yellow text is readable!")
        except Exception as e:
            print(f"❌ Test caption failed: {e}")
        return

    # --- Test Video Mode ---
    # Generates a full test video from either a local sample story or a custom file without fetching new stories or uploading.
    if args.test_video or args.test_story_file:
        print("\n🧪 TEST VIDEO MODE")
        print("Generating a test video locally without fetching new stories or uploading...\n")
        
        # Check if we're testing inspiration content
        if args.content_type == "inspiration":
            print("🏛️ Testing INSPIRATION (Dark Stoic) content type\n")
            
            result = create_inspirational_short(
                youtube_client=None,
                history=None,
                voice=args.voice
            )
            
            if result['success'] and result.get('file_path'):
                print("\n" + "=" * 60)
                print("🎉 TEST INSPIRATION VIDEO SUCCESSFUL!")
                print(f"   Video saved at: {os.path.abspath(result['file_path'])}")
                print(f"   Theme: {result.get('stoic_theme', 'N/A')}")
                print("   Review: white text, dark background, calmer zoom, deeper voice")
                print("=" * 60 + "\n")
            else:
                print("\n❌ TEST INSPIRATION VIDEO FAILED. See error output above.")
            return
        
        # Default: Story test mode
        test_title = "My entitled neighbor tried to claim half my backyard, so I built a 10-foot spite fence."
        test_body = (
            "My neighbor, Karen, decided that since there was no fence between our yards, she owned the line of oak trees on my property. "
            "She actually hired landscapers to cut them down. I ran outside and stood in front of the trees, telling them they were trespassing. "
            "Karen screamed at me, saying I was ruining her view. So, I went to the city hall, pulled the property line records, and proved the trees were entirely mine. "
            "Then, I hired contractors to build a 10-foot tall solid wood spite fence right along the boundary line. Now, her view is a literal blank wall, and she is furious."
        )
        test_subreddit = "pettyrevenge"
        
        if args.test_story_file:
            if not os.path.exists(args.test_story_file):
                print(f"❌ Custom story file not found: {args.test_story_file}")
                return
            try:
                with open(args.test_story_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if not lines:
                    print(f"❌ Story file is empty: {args.test_story_file}")
                    return
                test_title = lines[0].strip()
                test_body = "".join(lines[1:]).strip()
                test_subreddit = "custom_test"
                print(f"📖 Loaded custom story from file: {args.test_story_file}")
                print(f"   Title: {test_title[:60]}...")
            except Exception as e:
                print(f"❌ Failed to read custom story file: {e}")
                return
        
        # Override upload settings for testing
        args.no_upload = True
        
        print(f"📖 Using test story:")
        print(f"   Title: {test_title}")
        print(f"   Subreddit: r/{test_subreddit}")
        print(f"   Length: {len(test_body.split())} words")
        
        result = create_and_upload_viral_short(
            youtube_client=None,
            history=None,
            voice=args.voice,
            background_path=args.background,
            test_story=(test_title, test_body, test_subreddit)
        )
        
        if result['success'] and result['file_path']:
            print("\n" + "=" * 60)
            print("🎉 TEST VIDEO GENERATION SUCCESSFUL!")
            print(f"   Video saved at: {os.path.abspath(result['file_path'])}")
            print("   You can now open the video to review voiceover style, script, and caption synchronization.")
            print("=" * 60 + "\n")
        else:
            print("\n❌ TEST VIDEO GENERATION FAILED. See error output above.")
        return

    print("\n" + "=" * 60)
    print("🚀 VIRAL SHORTS GENERATION PIPELINE")
    print(f"   Videos to generate: {args.num}")
    print(f"   Upload enabled: {not args.no_upload}")
    if args.voice:
        print(f"   Forced Voice: {args.voice}")
    if args.background:
        print(f"   Forced Background: {args.background}")
    if args.schedule:
        print(f"   Schedule: {args.schedule}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    content_type = args.content_type
    print(f"   Content Type: {content_type}")
    print("=" * 60)

    # --- Scheduling Logic ---
    if args.schedule:
        target_hour = {"morning": 10, "afternoon": 14, "evening": 19}.get(args.schedule)
        if target_hour is not None:
            now = datetime.now()
            target_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            
            # If target time has already passed today, schedule for tomorrow
            if now > target_time:
                target_time += timedelta(days=1)
                
            wait_seconds = (target_time - now).total_seconds()
            print(f"\n⏰ Scheduled for {args.schedule} ({target_time.strftime('%I:%M %p')}).")
            print(f"💤 Sleeping for {int(wait_seconds / 60)} minutes...")
            time.sleep(wait_seconds)
            print("🚀 Waking up and starting generation!")

    # Load upload history for deduplication
    history = load_upload_history()
    print(f"📚 Upload history: {len(history.get('uploaded_titles', []))} previous videos")

    # Authenticate with YouTube (skip if --no-upload is active)
    youtube_client = None
    if not args.no_upload:
        try:
            youtube_client = get_authenticated_service()
            print("✅ YouTube API authenticated")
        except Exception as e:
            print(f"⚠️ YouTube auth failed: {e}")
            print("Videos will be generated locally but not uploaded.")
    else:
        print("⏭️ Upload disabled by user. Skipping authentication.")

    # Generate and upload videos
    successful = 0
    for i in range(args.num):
        print("\n" + "\u2500" * 60)
        print(f"\U0001F4F9 VIDEO {i + 1} of {args.num} ({content_type.upper()})")
        print("\u2500" * 60)

        if content_type == "inspiration":
            result = create_inspirational_short(
                youtube_client=youtube_client,
                history=history,
                voice=args.voice
            )
        elif content_type == "would_you_rather":
            result = create_wyr_short(
                youtube_client=youtube_client,
                history=history,
                voice=args.voice
            )
        elif content_type == "fake_text":
            result = create_fake_text_short(
                youtube_client=youtube_client,
                history=history,
                voice=args.voice
            )
        elif content_type == "dark_psychology":
            result = create_dark_psych_short(
                youtube_client=youtube_client,
                history=history,
                voice=args.voice
            )
        elif content_type == "true_crime":
            result = create_true_crime_short(
                youtube_client=youtube_client,
                history=history,
                voice=args.voice
            )
        elif content_type == "number_facts":
            result = create_number_facts_short(
                youtube_client=youtube_client,
                history=history,
                voice=args.voice
            )
        elif content_type == "history":
            result = create_history_short(
                youtube_client=youtube_client,
                history=history,
                voice=args.voice
            )
        elif content_type == "quiz":
            result = create_quiz_short(
                youtube_client=youtube_client,
                history=history,
                voice=args.voice
            )
        else:
            result = create_and_upload_viral_short(
                youtube_client=youtube_client,
                history=history,
                voice=args.voice,
                background_path=args.background
            )

        if result['success'] and result['title']:
            successful += 1
            # Record in history
            history["uploaded_titles"].append(result['title'])
            video_record = {
                "title": result['title'],
                "video_id": result.get('video_id'),
                "uploaded_at": datetime.now().isoformat(),
                "file": result.get('file_path'),
                "content_type": content_type,
            }
            # Track themes for the different content types
            if result.get('stoic_theme'):
                video_record["stoic_theme"] = result['stoic_theme']
            if result.get('wyr_theme'):
                video_record["wyr_theme"] = result['wyr_theme']
            if result.get('ft_theme'):
                video_record["ft_theme"] = result['ft_theme']
            if result.get('psych_topic'):
                video_record["psych_topic"] = result['psych_topic']
            if result.get('horror_topic'):
                video_record["horror_topic"] = result['horror_topic']
            if result.get('number_theme'):
                video_record["number_theme"] = result['number_theme']
            if result.get('history_theme'):
                video_record["history_theme"] = result['history_theme']
            if result.get('quiz_theme'):
                video_record["quiz_theme"] = result['quiz_theme']
                
            history["videos"].append(video_record)
            save_upload_history(history)
            if result.get('video_id'):
                print(f"\n  💡 PRO TIP: Go to YouTube Studio and link a 'Related Video' to {result.get('video_id')}!")
                print(f"     This is the best way to convert Shorts viewers into long-form subscribers.")

        # Cooldown between uploads (skip for last video)
        # Randomized to look human — fixed intervals get flagged as bot behavior
        if i < args.num - 1 and result['success'] and youtube_client:
            if args.cooldown > 0:
                cooldown = args.cooldown
            else:
                cooldown = random.randint(UPLOAD_COOLDOWN_MIN, UPLOAD_COOLDOWN_MAX)
            print(f"\n  ⏳ Cooling down {cooldown}s before next video (randomized)...")
            time.sleep(cooldown)

    # Summary
    print("\n" + "=" * 60)
    print(f"✅ PIPELINE COMPLETE: {successful}/{args.num} videos generated/uploaded")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_pipeline()
