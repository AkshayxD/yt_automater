import requests
import random
import re

def clean_text(text):
    """Removes URLs and weird characters that TTS might struggle with."""
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s.,!?\'"-]', '', text)
    return text.strip()

def get_reddit_story():
    """
    Scrapes a popular post from a random viral subreddit using Reddit's public JSON API.
    Returns a tuple: (title, story_text)
    """
    subreddits = [
        "pettyrevenge", "confession", "tifu", "EntitledParents", 
        "TrueOffMyChest", "AmItheAsshole", "MaliciousCompliance", "NuclearRevenge"
    ]
    
    # We must use a descriptive bot User-Agent as per Reddit's API guidelines to avoid 403 errors.
    headers = {
        'User-Agent': 'python:yt_automater_bot:v1.0 (by /u/automation)'
    }
    
    # Words that usually indicate a sad vent rather than an entertaining story
    boring_keywords = ['tired', 'depressed', 'suicide', 'kill myself', 'give up', 'sad', 'crying', 'lonely']
    
    # Try up to 5 times to find a valid post
    for attempt in range(5):
        subreddit = random.choice(subreddits)
        timeframe = random.choice(["day", "week", "month", "year", "all"])
        
        print(f"Attempt {attempt+1}: Fetching from r/{subreddit} (Top of the {timeframe})...")
        url = f"https://www.reddit.com/r/{subreddit}/top.json?limit=100&t={timeframe}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            posts = data['data']['children']
            valid_posts = []
            
            for post in posts:
                post_data = post['data']
                if post_data.get('selftext'):
                    body = post_data['selftext'].lower()
                    title = post_data['title'].lower()
                    
                    if any(word in body for word in boring_keywords) or any(word in title for word in boring_keywords):
                        continue
                        
                    word_count = len(body.split())
                    # Increase minimum to 115 words so the story feels "full" (approx 40-55 seconds)
                    if 115 < word_count < 175:
                        valid_posts.append(post_data)
            
            if valid_posts:
                chosen = random.choice(valid_posts)
                title = clean_text(chosen['title'])
                body = clean_text(chosen['selftext'])
                return title, body
                
        except Exception as e:
            print(f"Error fetching from Reddit on attempt {attempt+1}: {e}")
            
    # Fallback if ALL 5 attempts fail
    return ("Why I love automation", "Automation is great because it does the work for you while you sleep. I built a bot that makes videos, and now I just watch it go. It's the best feeling in the world. Subscribe for more tech tips.")

if __name__ == "__main__":
    title, body = get_reddit_story()
    print(f"Title: {title}")
    print(f"Body: {body[:100]}...")
