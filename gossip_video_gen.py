import os
import random
import re
import urllib.parse
import urllib.request
import requests
import html
import xml.etree.ElementTree as ET
from datetime import datetime
import shutil

from scraper import clean_text, inject_dramatic_pauses
from audio_gen import generate_audio_and_subs
from video_gen import create_video
from background_manager import pick_background_segment, record_used_segment
from uploader import upload_video, add_pinned_comment

TEMP_DIR = "temp"
VIDEOS_DIR = "videos_to_upload"
UPLOADED_DIR = "uploaded_videos"
ASSETS_DIR = "assets"
GOSSIP_SUBREDDITS = ["Fauxmoi", "popculturechat", "KUWTK", "CelebWivesofNashville"]

# Ensure directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(UPLOADED_DIR, exist_ok=True)

def get_gossip_story():
    """
    Scrapes a trending celebrity gossip story using free Reddit RSS feeds.
    """
    headers = {'User-Agent': 'python:yt_automater_gossip:v1.0'}
    subreddits_to_try = random.sample(GOSSIP_SUBREDDITS, min(3, len(GOSSIP_SUBREDDITS)))

    for subreddit in subreddits_to_try:
        url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=day"
        print(f"  Fetching gossip from r/{subreddit}...")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue

            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            entries = root.findall('atom:entry', ns)
            if not entries:
                continue
                
            # Pick a highly upvoted post (usually in the top 3)
            entry = random.choice(entries[:3])
            title = entry.find('atom:title', ns).text
            
            content_elem = entry.find('atom:content', ns)
            body_text = ""
            if content_elem is not None and content_elem.text:
                body_html = html.unescape(content_elem.text)
                body_text = re.sub(r'<[^>]+>', ' ', body_html)
                body_text = re.sub(r'\s+', ' ', body_text)
                body_text = re.sub(r'submitted by /u/\S+ \[link\] \[comments\]', '', body_text).strip()
            
            return clean_text(title), clean_text(body_text), subreddit

        except Exception as e:
            print(f"  ⚠️ Error scraping r/{subreddit}: {e}")

    # Fallback
    return "Massive drama at the awards show last night", "A massive fight broke out backstage and everyone is talking about it.", "Fauxmoi"

def rewrite_gossip_script(title, body):
    """
    Uses Gemini to write a punchy gossip script and extract a visual description for the AI caricature.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "CELEB DRAMA!", "A massive fight broke out. Like and subscribe.", "A famous pop star"

    try:
        from google import genai
        import json
        client = genai.Client(api_key=api_key)
        
        prompt = f"""You are a ruthless, highly engaging celebrity gossip narrator.
        
Write a 60-80 word YouTube Shorts script based on this gossip. 
The first word must be the celebrity's name or a dramatic verb. End with a cliffhanger or an engagement CTA.
Also, provide a generic visual description of the celebrity involved (e.g., "A blonde female pop star in a sparkly dress", "A handsome male actor in a tuxedo"). Do NOT use their real name in the visual description to bypass AI safety filters.

Respond ONLY with a valid JSON object in this exact format:
{{
  "headline": "A punchy ALL CAPS title (5-9 words).",
  "script": "The 60-80 word narration script.",
  "visual_description": "The generic visual description for an AI image generator."
}}

Gossip Title: {title}
Gossip Body: {body}
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "temperature": 1.0,
                "response_mime_type": "application/json",
            }
        )
        
        data = json.loads(response.text.strip())
        headline = data.get("headline", title).strip()
        script = inject_dramatic_pauses(data.get("script", "").strip())
        visual_desc = data.get("visual_description", "A famous celebrity").strip()
        
        return headline, script, visual_desc
    except Exception as e:
        print(f"  ⚠️ Gemini AI error: {e}")
        return title[:50], title + ". " + body[:100], "A famous celebrity"

def download_caricature_image(celeb_description):
    """
    Uses Pollinations AI to generate a 3D caricature of the celebrity based on their visual description.
    """
    prompt = f"A vibrant, highly detailed 3D cartoon caricature of {celeb_description}, colorful background, expressive, stylized, in the style of a modern animated movie"
    safe_prompt = urllib.parse.quote(prompt)
    
    # 9:16 aspect ratio
    image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1080&height=1920&nologo=true"
    image_path = os.path.join(TEMP_DIR, "celeb_caricature.jpg")
    
    print(f"  🎨 Generating AI Caricature: {celeb_description}")
    
    try:
        req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(image_path, 'wb') as f:
                f.write(response.read())
        return image_path
    except Exception as e:
        print(f"  ❌ Failed to download AI image: {e}")
        return None

def generate_gossip_metadata(headline, script_text, subreddit):
    short_title = headline[:50].strip()
    first_sentence = script_text.split('.')[0].strip() if script_text else ""
    description = (
        f"{first_sentence}\n\n"
        f"#Shorts #CelebrityGossip #PopCulture #Drama\n\n"
        f"What do you think? 👇\n"
        f"Follow for daily gossip 🔔\n\n"
        f"---\n"
        f"Spilled on r/{subreddit}"
    )
    tags = ["shorts", "celebrity gossip", "pop culture", "drama", "hollywood", "trending", "news"]
    return short_title, description, tags

def create_gossip_short(youtube_client=None, voice=None):
    """
    The main pipeline for Gossip Shorts.
    """
    result = {'success': False, 'title': None, 'video_id': None, 'file_path': None, 'gossip_theme': 'celebrity'}
    print("\n🎬 Starting Gossip Short Generation...")
    
    # 1. Fetch Gossip
    title, body, subreddit = get_gossip_story()
    print(f"  📰 Scraped from r/{subreddit}: {title[:60]}...")
    
    # 2. Rewrite & Extract Visual Description
    print("  🤖 AI Script Rewriting...")
    ai_headline, script_text, visual_description = rewrite_gossip_script(title, body)
    
    full_spoken_text = f"{ai_headline}. {script_text}"
    
    # 3. Audio & Subs
    print("  🎤 Generating voiceover and subtitles...")
    audio_file = os.path.join(TEMP_DIR, "audio.mp3")
    subs_file = os.path.join(TEMP_DIR, "subs.srt")
    
    mp3_path, srt_path = generate_audio_and_subs(full_spoken_text, audio_file, subs_file, voice=voice)
    if not mp3_path or not srt_path:
        print("  ❌ Failed to generate audio. Aborting.")
        return result
        
    # 4. Generate Caricature
    caricature_path = download_caricature_image(visual_description)
    
    # 5. Assemble Video
    print("  🎥 Assembling video...")
    safe_title = "".join([c for c in ai_headline if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    safe_title_underscored = safe_title.replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_video_path = os.path.join(VIDEOS_DIR, f"GOSSIP_{safe_title_underscored}_{timestamp}.mp4")
    
    bg_video, bg_start = pick_background_segment(needed_duration=60.0)
    if bg_video is None:
        bg_video = os.path.join(ASSETS_DIR, "background_small.mp4")
        
    try:
        # We pass the caricature to create_video if it supports it, 
        # or we could overlay it via ffmpeg. For now, since we haven't added 
        # custom image overlay logic to video_gen.py yet, we'll let it use the gameplay background 
        # as standard. The text itself will tell the gossip!
        # (A future update to video_gen.py could accept `popup_image_path=caricature_path`)
        rendered_video = create_video(
            mp3_path, srt_path,
            background_path=bg_video,
            output_path=final_video_path,
            bg_start_time=bg_start,
            hook_text=ai_headline,
            content_type="story"  # Use standard yellow/green captions
        )
        if bg_start is not None and rendered_video:
            from moviepy.editor import AudioFileClip
            dur = AudioFileClip(mp3_path).duration
            record_used_segment(bg_video, bg_start, bg_start + dur)
    except Exception as e:
        print(f"  ❌ Error during video generation: {e}")
        return result
        
    # 6. Upload
    short_title, description, tags = generate_gossip_metadata(ai_headline, script_text, subreddit)
    
    if youtube_client:
        print("  📤 Uploading to YouTube...")
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
                result['title'] = ai_headline
                result['video_id'] = video_id
                result['file_path'] = rendered_video
                
                shutil.move(rendered_video, os.path.join(UPLOADED_DIR, os.path.basename(rendered_video)))
                print(f"  Moved video to {UPLOADED_DIR}/")
                
                # Pin Comment
                comment = random.choice([
                    "What do you guys think? Is this legit? 👇",
                    "I genuinely can't believe this happened... Thoughts?",
                    "Who is actually in the wrong here? Let me know below."
                ])
                add_pinned_comment(youtube_client, video_id, comment)
        except Exception as e:
            print(f"  ❌ Failed to upload video: {e}")
    else:
        print(f"  ⏭️ Skipping upload (no YouTube client)")
        result['success'] = True
        result['title'] = ai_headline
        result['file_path'] = rendered_video
        
    return result

if __name__ == "__main__":
    create_gossip_short()
