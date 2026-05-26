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
UPLOAD_COOLDOWN = 300  # 5 minutes between uploads to avoid spam flags
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
    
    Returns: (short_title, description, tags)
    """
    # --- TITLE ---
    # Short, curiosity-driven, under 60 chars, NO #shorts in title
    # Try to extract the most dramatic phrase

    # Strategy 1: If title has a question, use it directly (shortened)
    if '?' in title and len(title) < 60:
        short_title = title
    else:
        # Strategy 2: Create a curiosity gap from the title
        # Truncate at a natural break point
        short_title = title[:57]
        # Try to cut at a word boundary
        last_space = short_title.rfind(' ')
        if last_space > 30:
            short_title = short_title[:last_space]

        # Add an emotional hook if the title feels flat
        if not any(c in short_title for c in '?!'):
            # Check for dramatic keywords and add emphasis
            short_title_lower = short_title.lower()
            for kw in ['caught', 'fired', 'revenge', 'karma', 'exposed', 'cheating']:
                if kw in short_title_lower:
                    short_title += " 😱"
                    break
            else:
                short_title += "..."

    # Ensure we're under 60 chars
    if len(short_title) > 60:
        short_title = short_title[:57] + "..."

    # --- DESCRIPTION ---
    # Hook line + hashtags + CTA
    # Extract first compelling sentence from the body
    first_sentence = body.split('.')[0].strip() if body else ""
    if len(first_sentence) > 150:
        first_sentence = first_sentence[:147] + "..."

    # Map subreddits to relevant hashtags
    subreddit_hashtags = {
        "pettyrevenge": "#Revenge #PettyRevenge",
        "prorevenge": "#Revenge #ProRevenge #Justice",
        "nuclearrevenge": "#Revenge #NuclearRevenge #Justice",
        "maliciouscompliance": "#MaliciousCompliance #Revenge",
        "confession": "#Confession #StoryTime",
        "tifu": "#TIFU #FunnyStory",
        "entitledparents": "#EntitledParents #Karen",
        "trueoffmychest": "#TrueOffMyChest #Confession",
        "amitheasshole": "#AITA #AmITheAsshole",
        "choosingbeggars": "#ChoosingBeggars #Entitled",
        "idontworkherelady": "#IDontWorkHereLady #Karen",
        "relationships": "#Relationships #Drama",
        "neighborsfromhell": "#BadNeighbors #Neighbors",
        "bestofredditorupdates": "#RedditUpdates #StoryTime",
    }

    sub_tags = subreddit_hashtags.get(subreddit.lower(), "#RedditStories")

    description = (
        f"{first_sentence}\n\n"
        f"#Shorts {sub_tags} #RedditStories #StoryTime\n\n"
        f"Follow for daily stories! 🔔\n\n"
        f"---\n"
        f"Story from r/{subreddit}"
    )

    # --- TAGS ---
    # Mix of broad + niche keywords
    base_tags = ["shorts", "reddit stories", "storytime", "reddit", "true stories"]

    # Add topic-specific tags based on content
    body_lower = body.lower()
    topic_tags = []
    topic_map = {
        "revenge": ["revenge story", "karma", "justice"],
        "boss": ["work story", "bad boss", "quit job"],
        "wedding": ["wedding drama", "bridezilla"],
        "neighbor": ["bad neighbor", "neighbor story"],
        "cheating": ["cheating story", "relationship drama"],
        "parent": ["entitled parents", "family drama"],
        "school": ["school story", "teacher story"],
        "roommate": ["roommate story", "living together"],
        "divorce": ["divorce story", "relationship"],
    }

    for keyword, tags in topic_map.items():
        if keyword in body_lower:
            topic_tags.extend(tags)

    # Subreddit-based tags
    sub_name_clean = subreddit.lower().replace("_", " ")
    topic_tags.append(sub_name_clean)

    all_tags = base_tags + list(set(topic_tags))  # Deduplicate
    # YouTube allows max 500 chars of tags — keep it reasonable
    all_tags = all_tags[:15]

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

        # Safety check on length (prevent 60s+ Shorts) — target is 110-125 words
        if len(full_spoken_text.split()) > 160:
            print("  ⚠️ Script unusually long — trimming")
            trimmed = ' '.join(full_spoken_text.split()[:130])
            
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
                    # If it's part 1 of a multi-part series, pin a comment linking to the profile.
                    # If it's part 2 or a single video, pin a comment asking the "Who was right?" question.
                    try:
                        from uploader import add_pinned_comment
                        if part['suffix'] == " (Part 1)":
                            comment_text = "Part 2 is on my profile! Subscribe so you don't miss the ending 👇"
                        else:
                            comment_text = "Who do you think was right? Let me know down below! 👇"
                        
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
    parser.add_argument("-c", "--cooldown", type=int, default=300, 
                        help="Cooldown seconds between uploads (default: 300)")

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
        if i < args.num - 1 and result['success'] and youtube_client:
            print(f"\n  ⏳ Cooling down {args.cooldown}s before next video...")
            time.sleep(args.cooldown)

    # Summary
    print("\n" + "=" * 60)
    print(f"✅ PIPELINE COMPLETE: {successful}/{args.num} videos generated/uploaded")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_pipeline()
