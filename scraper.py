import requests
import random
import re
import os

def clean_text(text):
    """Removes URLs and weird characters that TTS might struggle with."""
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s.,!?\'"-]', '', text)
    return text.strip()

def get_reddit_story():
    """
    Scrapes a popular post from a random viral subreddit using Reddit's API.
    Uses OAuth2 if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are provided.
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
    
    # Try to authenticate using OAuth2 if credentials are provided via GitHub Secrets
    client_id = os.environ.get('REDDIT_CLIENT_ID')
    client_secret = os.environ.get('REDDIT_CLIENT_SECRET')
    access_token = None
    
    if client_id and client_secret:
        try:
            client_auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
            post_data = {"grant_type": "client_credentials"}
            res = requests.post("https://www.reddit.com/api/v1/access_token", auth=client_auth, data=post_data, headers=headers)
            res.raise_for_status()
            access_token = res.json().get('access_token')
            print("Successfully obtained Reddit API OAuth access token.")
        except Exception as e:
            print(f"Failed to authenticate with Reddit API: {e}")
            
    # Words that usually indicate a sad vent rather than an entertaining story
    boring_keywords = ['tired', 'depressed', 'suicide', 'kill myself', 'give up', 'sad', 'crying', 'lonely']
    
    # Try up to 5 times to find a valid post
    for attempt in range(5):
        subreddit = random.choice(subreddits)
        timeframe = random.choice(["day", "week", "month", "year", "all"])
        
        print(f"Attempt {attempt+1}: Fetching from r/{subreddit} (Top of the {timeframe})...")
        
        req_headers = headers.copy()
        if access_token:
            url = f"https://oauth.reddit.com/r/{subreddit}/top.json?limit=100&t={timeframe}"
            req_headers['Authorization'] = f"bearer {access_token}"
        else:
            url = f"https://www.reddit.com/r/{subreddit}/top.json?limit=100&t={timeframe}"
        
        try:
            response = requests.get(url, headers=req_headers)
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
