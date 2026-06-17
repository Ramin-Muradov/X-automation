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
Analyze the X (Twitter) Explore / Trending sections globally. Focus on the three categories: "Technology", "Business and Finance", and "Cryptocurrency".
What are the top 10 most active trending topics, hashtags, or keywords under these categories in the last 24 hours?
Return ONLY a comma-separated list of these keywords or hashtags, without '#' symbol (e.g. Nvidia, Bitcoin, OpenAI, inflation, Ethereum). Do not include any other text.
"""

try:
    print("Asking Grok for current trending keywords...")
    response = client.chat.completions.create(
        model="grok-3-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a real-time data analyst for X (Twitter). Return ONLY the requested comma-separated list."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=200
    )
    
    raw_keywords = response.choices[0].message.content.strip()
    keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]
    print(f"Grok returned keywords: {keywords}")
    
    # Build search query
    keywords_query = " OR ".join([f'"{k}"' for k in keywords[:10]])
    query = f"has:videos ({keywords_query}) -is:reply -is:retweet"
    print(f"X API Search Query: {query}")
    
    from datetime import datetime, timezone, timedelta
    start_time_dt = datetime.now(timezone.utc) - timedelta(hours=24)
    start_time = start_time_dt.isoformat().replace("+00:00", "Z")
    
    print("Searching X API...")
    tweets = twitter.search_video_tweets(query, start_time=start_time, max_results=100)
    print(f"Found {len(tweets)} video tweets.")
    
    # Filter by follower threshold (e.g., 50k) or verified status
    valid_tweets = []
    for t in tweets:
        followers = t.get("followers_count", 0)
        is_verified = t.get("verified", False)
        if followers >= 50000 or is_verified:
            valid_tweets.append(t)
            
    print(f"Filtered down to {len(valid_tweets)} authoritative tweets.")
    
    # Sort by views
    valid_tweets.sort(key=lambda x: x["public_metrics"].get("impression_count", 0), reverse=True)
    
    print("\nTop 15 Video Tweets Sorted by Views:")
    for idx, vt in enumerate(valid_tweets[:15]):
        views = vt["public_metrics"].get("impression_count", 0)
        print(f"  [{idx}] by @{vt['username']} (Followers: {vt['followers_count']}) | Views: {views} | Likes: {vt['public_metrics'].get('like_count', 0)} | Text: {vt['text'][:80]}...")
        
except Exception as e:
    print(f"Error: {e}")
