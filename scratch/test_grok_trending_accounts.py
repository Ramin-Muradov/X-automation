import os
import json
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from src.twitter_client import TwitterClient
from config.settings import settings

client = OpenAI(
    api_key=settings.GROK_API_KEY,
    base_url=settings.GROK_BASE_URL,
)
twitter = TwitterClient()

prompt = """
Analyze the global X (Twitter) Explore / Trending sections. Under the categories "Technology", "Business and Finance", and "Cryptocurrency", identify the top 5 X accounts that posted the most viral, highly viewed video tweets (with hundreds of thousands or millions of views) in the last 24 hours.

Return ONLY a comma-separated list of their exact X usernames (without @, e.g. elonmusk, Bloomberg, vitalikbuterin). Do not include any other text.
"""

try:
    print("Asking Grok for viral accounts...")
    response = client.chat.completions.create(
        model="grok-3-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a real-time data analyst for X (Twitter). Return ONLY the requested comma-separated list of real usernames."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=200
    )
    
    raw_usernames = response.choices[0].message.content.strip()
    usernames = [u.strip() for u in raw_usernames.split(",") if u.strip()]
    print(f"Grok returned usernames: {usernames}")
    
    # Filter valid usernames (max 15 chars, alphanumeric/underscores)
    clean_usernames = []
    for u in usernames:
        clean_u = "".join(c for c in u if c.isalnum() or c == "_")
        if 1 <= len(clean_u) <= 15:
            clean_usernames.append(clean_u)
            
    print(f"Cleaned usernames: {clean_usernames}")
    
    if not clean_usernames:
        print("No valid usernames returned.")
        exit(1)
        
    # Query X API
    accounts_query = " OR ".join([f"from:{acc}" for acc in clean_usernames])
    query = f"has:videos ({accounts_query})"
    print(f"X API Query: {query}")
    
    from datetime import datetime, timezone, timedelta
    start_time_dt = datetime.now(timezone.utc) - timedelta(hours=24)
    start_time = start_time_dt.isoformat().replace("+00:00", "Z")
    
    tweets = twitter.search_video_tweets(query, start_time=start_time, max_results=50)
    print(f"Found {len(tweets)} video tweets.")
    
    # Sort by views
    tweets.sort(key=lambda x: x["public_metrics"].get("impression_count", 0), reverse=True)
    
    print("\nTweets found sorted by views:")
    for idx, t in enumerate(tweets):
        views = t["public_metrics"].get("impression_count", 0)
        print(f"  [{idx}] by @{t['username']} | Views: {views} | Likes: {t['public_metrics'].get('like_count', 0)} | Text: {t['text'][:80]}...")
        
except Exception as e:
    print(f"Error: {e}")
