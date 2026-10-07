import os
import random
import re
import html
import requests
import xml.etree.ElementTree as ET

from scraper import clean_text

def get_glitch_story():
    """
    Scrapes a story from r/Glitch_in_the_Matrix or r/MandelaEffect
    """
    headers = {'User-Agent': 'python:yt_automater_glitch:v1.0'}
    subreddits = ["Glitch_in_the_Matrix", "MandelaEffect", "HighStrangeness"]
    subreddit = random.choice(subreddits)
    
    url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=week"
    try:
        response = requests.get(url, headers=headers, timeout=15)
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)
        if entries:
            entry = random.choice(entries[:5])
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
        print(f"  ⚠️ Error scraping glitch: {e}")
        
    return "I saw my own doppelganger", "I was walking down the street and I saw myself walking towards me.", "Glitch_in_the_Matrix"

def generate_glitch_script():
    """
    Uses Gemini to rewrite a Glitch story.
    """
    title, body, subreddit = get_glitch_story()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "GLITCH IN THE MATRIX", "I saw a glitch in the matrix today. " + body[:100]

    try:
        from google import genai
        import json
        client = genai.Client(api_key=api_key)
        
        prompt = f"""You are a narrator for a creepy, unsolved mysteries YouTube Shorts channel.
        
Write a 60-80 word script based on this true creepy glitch/mystery story. 
The first sentence MUST be a dramatic hook. Build tension. 
End the script with a cliffhanger and an engagement CTA asking if viewers have ever experienced this.

Respond ONLY with a valid JSON object in this format:
{{
  "headline": "A punchy ALL CAPS title (5-9 words)",
  "script": "The 60-80 word narration script."
}}

Story Title: {title}
Story Body: {body}
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
        script = data.get("script", "").strip()
        
        return headline, script
    except Exception as e:
        print(f"  ⚠️ Gemini AI error: {e}")
        return "GLITCH IN THE MATRIX", "I saw a glitch in the matrix today. " + body[:100]
