import os
from dotenv import load_dotenv
load_dotenv()

from src.twitter_client import TwitterClient
from datetime import datetime, timezone, timedelta

client = TwitterClient()

window_hours = 24
start_time_dt = datetime.now(timezone.utc) - timedelta(hours=window_hours)
start_time = start_time_dt.isoformat().replace("+00:00", "Z")

query = 'has:videos ("technology" OR "business" OR "finance" OR "cryptocurrency" OR "crypto" OR "bitcoin" OR "ethereum" OR "tech" OR "market" OR "economy" OR "economics" OR "tax" OR "spending" OR "inflation" OR "money" OR "stocks" OR "investing") min_replies:15 -is:reply -is:retweet'

print(f"Query: {query}")
try:
    response = client.client_v2.search_recent_tweets(
        query=query,
        start_time=start_time,
        max_results=100,
        sort_order="relevancy",
        tweet_fields=["public_metrics", "created_at", "author_id"],
        expansions=["author_id"],
        user_fields=["public_metrics", "verified"]
    )
    
    user_map = {}
    if response.includes and "users" in response.includes:
        for u in response.includes["users"]:
            followers = 0
            if u.public_metrics and "followers_count" in u.public_metrics:
                followers = u.public_metrics["followers_count"]
            user_map[u.id] = {
                "username": u.username,
                "followers_count": followers,
                "verified": getattr(u, "verified", False)
            }

    print(f"\nResults (Total: {len(response.data) if response.data else 0}):")
    if response.data:
        processed_tweets = []
        for t in response.data:
            user_info = user_map.get(t.author_id, {"username": "i", "followers_count": 0, "verified": False})
            views = t.public_metrics.get("impression_count", 0)
            processed_tweets.append((t, user_info, views))
            
        processed_tweets.sort(key=lambda x: x[2], reverse=True)
        
        for idx, (t, user_info, views) in enumerate(processed_tweets[:30]):
            print(f"  [{idx}] by @{user_info['username']} (Followers: {user_info['followers_count']}) | Views: {views} | Replies: {t.public_metrics.get('reply_count', 0)} | Likes: {t.public_metrics.get('like_count', 0)} | Text: {t.text[:80]}...")
except Exception as e:
    print(f"Error: {e}")
