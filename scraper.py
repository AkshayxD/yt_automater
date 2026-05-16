import requests
import random
import re
import html
import xml.etree.ElementTree as ET

def clean_text(text):
    """Removes URLs and weird characters that TTS might struggle with."""
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s.,!?\'"-]', '', text)
    return text.strip()

def get_reddit_story():
    """
    Scrapes a popular post from a random viral subreddit using Reddit's RSS Feeds.
    This completely bypasses the 403 blocks on GitHub Actions without needing API keys!
    Returns a tuple: (title, story_text)
    """
    subreddits = [
        "pettyrevenge", "confession", "tifu", "EntitledParents", 
        "TrueOffMyChest", "AmItheAsshole", "MaliciousCompliance", "NuclearRevenge"
    ]
    
    # We must use a descriptive bot User-Agent
    headers = {
        'User-Agent': 'python:yt_automater_bot:v2.0 (by /u/automation)'
    }
            
    # Words that usually indicate a sad vent rather than an entertaining story
    boring_keywords = ['tired', 'depressed', 'suicide', 'kill myself', 'give up', 'sad', 'crying', 'lonely']
    
    # Try up to 5 times to find a valid post
    for attempt in range(5):
        subreddit = random.choice(subreddits)
        timeframe = random.choice(["day", "week", "month", "year", "all"])
        
        print(f"Attempt {attempt+1}: Fetching from r/{subreddit} (Top of the {timeframe}) via RSS...")
        
        url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t={timeframe}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            valid_posts = []
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text
                content_elem = entry.find('atom:content', ns)
                
                if content_elem is not None and content_elem.text:
                    body_html = html.unescape(content_elem.text)
                    
                    # Strip HTML tags
                    body_text = re.sub(r'<[^>]+>', ' ', body_html)
                    # Collapse multiple spaces
                    body_text = re.sub(r'\s+', ' ', body_text)
                    # Strip RSS footer (submitted by /u/... [link] [comments])
                    body_text = re.sub(r'submitted by /u/\S+ \[link\] \[comments\]', '', body_text).strip()
                    
                    body_lower = body_text.lower()
                    title_lower = title.lower()
                    
                    if any(word in body_lower for word in boring_keywords) or any(word in title_lower for word in boring_keywords):
                        continue
                        
                    word_count = len(body_text.split())
                    # Minimum 115 words so the story feels "full" (approx 40-55 seconds)
                    if 115 < word_count < 175:
                        valid_posts.append({'title': title, 'body': body_text})
            
            if valid_posts:
                chosen = random.choice(valid_posts)
                final_title = clean_text(chosen['title'])
                final_body = clean_text(chosen['body'])
                return final_title, final_body
                
        except Exception as e:
            print(f"Error fetching from Reddit on attempt {attempt+1}: {e}")
            
    # Fallback if ALL 5 attempts fail
    return ("Why I love automation", "Automation is great because it does the work for you while you sleep. I built a bot that makes videos, and now I just watch it go. It's the best feeling in the world. Subscribe for more tech tips.")

if __name__ == "__main__":
    title, body = get_reddit_story()
    print(f"Title: {title}")
    print(f"Body: {body[:100]}...")
