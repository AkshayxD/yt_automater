import os
import random
import re
import html
import requests
import xml.etree.ElementTree as ET

from scraper import clean_text

def get_shower_thoughts():
    """
    Scrapes 3 thoughts from r/Showerthoughts to combine into a rapid-fire script.
    """
    headers = {'User-Agent': 'python:yt_automater_shower:v1.0'}
    url = "https://www.reddit.com/r/Showerthoughts/top/.rss?t=week"
    thoughts = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)
        
        # Shuffle and pick 3 valid thoughts
        random.shuffle(entries)
        for entry in entries:
            title = entry.find('atom:title', ns).text
            # Shower thoughts are usually just the title. 
            # We want ones that are short and punchy.
            if 10 < len(title) < 120 and not any(w in title.lower() for w in ["reddit", "edit", "sub"]):
                thoughts.append(clean_text(title))
            if len(thoughts) >= 3:
                break
                
    except Exception as e:
        print(f"  ⚠️ Error scraping shower thoughts: {e}")
        
    if len(thoughts) < 3:
        thoughts = [
            "Water has different tastes based on its temperature.",
            "Your alarm sound is just your theme song for suffering.",
            "If you drop soap on the floor, is the floor clean or is the soap dirty?"
        ]
        
    return thoughts

def generate_shower_script():
    """
    Uses Gemini to format the 3 shower thoughts into a viral rapid-fire script.
    """
    thoughts = get_shower_thoughts()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        script = f"Mind blowing shower thoughts. {thoughts[0]}. {thoughts[1]}. {thoughts[2]}. Subscribe for more."
        return "MIND BLOWING THOUGHTS", script

    try:
        from google import genai
        import json
        client = genai.Client(api_key=api_key)
        
        prompt = f"""You are a fast-paced YouTube Shorts creator.
        
Combine these 3 "shower thoughts" into a rapid-fire, 60-80 word narration script.
The hook MUST be dramatic (e.g. "Thoughts that will ruin your day" or "Things that don't make sense").
Deliver the thoughts quickly.
End with a call to action asking them to subscribe if their mind was blown.

Thought 1: {thoughts[0]}
Thought 2: {thoughts[1]}
Thought 3: {thoughts[2]}

Respond ONLY with a valid JSON object in this format:
{{
  "headline": "A punchy ALL CAPS title (5-9 words)",
  "script": "The 60-80 word narration script."
}}
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
        headline = data.get("headline", "MIND BLOWING THOUGHTS").strip()
        script = data.get("script", "").strip()
        
        return headline, script
    except Exception as e:
        print(f"  ⚠️ Gemini AI error: {e}")
        script = f"Mind blowing shower thoughts. {thoughts[0]}. {thoughts[1]}. {thoughts[2]}. Subscribe for more."
        return "MIND BLOWING THOUGHTS", script
