import os
import sys
from dotenv import load_dotenv
load_dotenv()

from src.twitter_client import TwitterClient
from config.settings import settings

client = TwitterClient()

print("Fetching global trending topics from X API (WOEID = 1)...")
try:
    # WOEID 1 is Global
    trends_response = client.api_v1.get_place_trends(id=1)
    trends = trends_response[0]["trends"]
    print(f"Successfully retrieved {len(trends)} global trends.")
    
    # Filter trends for tech, business, finance, crypto
    keywords = ["tech", "ai", "crypto", "bitcoin", "ethereum", "btc", "eth", "business", "finance", "market", "economy", "nvidia", "apple", "google", "meta", "microsoft", "tesla", "coin", "solana", "stock", "funding", "startup"]
    relevant_trends = []
    
    for t in trends:
        name = t["name"]
        query = t["query"]
        # Check if trend name matches any of our keywords
        matched = False
        for kw in keywords:
            if kw in name.lower():
                matched = True
                break
        if matched:
            relevant_trends.append(t)
            
    print(f"\nFound {len(relevant_trends)} relevant global trends:")
    for idx, rt in enumerate(relevant_trends[:10]):
        print(f"  [{idx}] Name: {rt['name']} | Query: {rt['query']}")
        
    if not relevant_trends:
        print("No relevant trends found. Using fallback hashtags: #tech, #business, #crypto")
        relevant_trends = [{"name": "#tech"}, {"name": "#business"}, {"name": "#crypto"}]
        
    # Search for videos in the top 3 relevant trends
    print("\nSearching for videos under top 3 relevant trends...")
    all_video_tweets = []
    seen_tweet_ids = set()
    
    from datetime import datetime, timezone, timedelta
    start_time_dt = datetime.now(timezone.utc) - timedelta(hours=24)
    start_time = start_time_dt.isoformat().replace("+00:00", "Z")
    
    for rt in relevant_trends[:3]:
        trend_name = rt["name"]
        print(f"  Searching for video tweets under trend: {trend_name}")
        search_query = f"has:videos {trend_name} -is:reply -is:retweet"
        try:
            results = client.search_video_tweets(search_query, start_time=start_time, max_results=20)
            print(f"    Found {len(results)} videos.")
            for tweet in results:
                if tweet["id"] not in seen_tweet_ids:
                    seen_tweet_ids.add(tweet["id"])
                    all_video_tweets.append(tweet)
        except Exception as e:
            print(f"    Error searching for trend {trend_name}: {e}")
            
    print(f"\nTotal unique video tweets found: {len(all_video_tweets)}")
    
    # Sort by views in Python
    all_video_tweets.sort(key=lambda x: x["public_metrics"].get("impression_count", 0), reverse=True)
    
    print("\nTop 15 Video Tweets Sorted by Views:")
    for idx, vt in enumerate(all_video_tweets[:15]):
        views = vt["public_metrics"].get("impression_count", 0)
        print(f"  [{idx}] by @{vt['username']} | Views: {views} | Likes: {vt['public_metrics'].get('like_count', 0)} | Text: {vt['text'][:80]}...")
        
except Exception as e:
    print(f"Error fetching trends: {e}")
