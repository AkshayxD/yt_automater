import os
import sys
import re
import json
import shutil
import time
import random
from datetime import datetime

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


def create_and_upload_viral_short(youtube_client=None, history=None, voice=None, background_path=None):
    """
    The main pipeline: fetch story -> voice -> video -> upload.
    
    Returns:
        dict with 'success', 'title', 'video_id', 'file_path' keys
    """
    result = {'success': False, 'title': None, 'video_id': None, 'file_path': None}

    # 1. Fetch Script (with dedup check)
    max_fetch_attempts = 3
    title, body, subreddit = None, None, None

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
                GLOW_COLOR, ACTIVE_FONT_SIZE, VIDEO_WIDTH, VIDEO_HEIGHT
            )
            # Create a dark background
            bg = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(30, 30, 40))
            bg = bg.set_duration(1)
            
            # Create test text with the caption style
            test_text = "KARMA"
            glow = TextClip(test_text, fontsize=ACTIVE_FONT_SIZE + 4,
                           color=GLOW_COLOR, font=FONT_NAME,
                           stroke_color=GLOW_COLOR, stroke_width=20,
                           method='label', align='center')
            stroke = TextClip(test_text, fontsize=ACTIVE_FONT_SIZE,
                             color='black', font=FONT_NAME,
                             stroke_color='black', stroke_width=STROKE_WIDTH,
                             method='label', align='center')
            txt = TextClip(test_text, fontsize=ACTIVE_FONT_SIZE,
                          color=ACTIVE_COLOR, font=FONT_NAME,
                          method='label', align='center')
            
            y_pos = int(VIDEO_HEIGHT * 0.55)
            glow = glow.set_position(('center', y_pos)).set_duration(1).set_opacity(0.55)
            stroke = stroke.set_position(('center', y_pos)).set_duration(1)
            txt = txt.set_position(('center', y_pos)).set_duration(1)
            
            # Composite and save (bar -> glow -> stroke -> text)
            frame = CompositeVideoClip([bg, glow, stroke, txt], size=(VIDEO_WIDTH, VIDEO_HEIGHT))
            output = os.path.join(TEMP_DIR, "test_caption.png")
            os.makedirs(TEMP_DIR, exist_ok=True)
            frame.save_frame(output, t=0)
            frame.close()
            
            print(f"✅ Test caption saved to: {os.path.abspath(output)}")
            print(f"   Color: {ACTIVE_COLOR}")
            print(f"   Font: {FONT_NAME}")
            print(f"   Size: {ACTIVE_FONT_SIZE}px | Stroke: {STROKE_WIDTH}px")
            print(f"   Glow: {GLOW_COLOR}")
            print("\nOpen the PNG file to verify the yellow text is readable!")
        except Exception as e:
            print(f"❌ Test caption failed: {e}")
        return

    print("\n" + "=" * 60)
    print("🚀 VIRAL SHORTS GENERATION PIPELINE")
    print(f"   Videos to generate: {args.num}")
    print(f"   Upload enabled: {not args.no_upload}")
    if args.voice:
        print(f"   Forced Voice: {args.voice}")
    if args.background:
        print(f"   Forced Background: {args.background}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

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
        print(f"\n{'─' * 60}")
        print(f"📹 VIDEO {i + 1} of {args.num}")
        print(f"{'─' * 60}")

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
            history["videos"].append({
                "title": result['title'],
                "video_id": result.get('video_id'),
                "uploaded_at": datetime.now().isoformat(),
                "file": result.get('file_path')
            })
            save_upload_history(history)

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
