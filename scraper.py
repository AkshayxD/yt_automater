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
    subreddits = ["pettyrevenge", "confession", "tifu", "EntitledParents"]
    subreddit = random.choice(subreddits)
    timeframe = random.choice(["day", "week", "month", "year", "all"])
    
    print(f"Fetching story from r/{subreddit} (Top of the {timeframe})...")
    url = f"https://www.reddit.com/r/{subreddit}/top.json?limit=100&t={timeframe}"
    
    # Reddit aggressively blocks fake browser user-agents from cloud IPs.
    # We must use a descriptive bot User-Agent as per Reddit's API guidelines to avoid 403 errors.
    headers = {
        'User-Agent': 'python:yt_automater_bot:v1.0 (by /u/automation)'
    }
    
    # Words that usually indicate a sad vent rather than an entertaining story
    boring_keywords = ['tired', 'depressed', 'suicide', 'kill myself', 'give up', 'sad', 'crying', 'lonely']
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        posts = data['data']['children']
        
        # Filter for text posts (selftext) that aren't too long
        valid_posts = []
        for post in posts:
            post_data = post['data']
            if post_data.get('selftext'):
                body = post_data['selftext'].lower()
                title = post_data['title'].lower()
                
                # Check for boring/depressing keywords
                if any(word in body for word in boring_keywords) or any(word in title for word in boring_keywords):
                    continue
                    
                word_count = len(body.split())
                # Shorts should ideally be around 60-175 words max to fit in 60s
                # We filter out longer stories so we NEVER have to cut them off abruptly.
                if 60 < word_count < 175:
                    valid_posts.append(post_data)
        
        if not valid_posts:
            # Fallback if no valid posts found
            return ("Why I love automation", "Automation is great because it does the work for you while you sleep. I built a bot that makes videos, and now I just watch it go. It's the best feeling in the world. Subscribe for more tech tips.")
            
        # Pick a random one from the valid ones
        chosen = random.choice(valid_posts)
        
        title = clean_text(chosen['title'])
        body = clean_text(chosen['selftext'])
        
        return title, body
        
    except Exception as e:
        print(f"Error fetching from Reddit: {e}")
        # Fallback story
        return ("My dog ate my homework", "I couldn't believe it. I woke up and my essay was in shreds. My dog just looked at me and wagged his tail. What could I do? I had to tell my teacher the oldest lie in the book. Subscribe if you love dogs.")

if __name__ == "__main__":
    title, body = get_reddit_story()
    print(f"Title: {title}")
    print(f"Body: {body[:100]}...")
