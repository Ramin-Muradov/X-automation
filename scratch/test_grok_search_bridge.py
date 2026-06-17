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
Identify 5 of the most viral, highly viewed video tweets (with hundreds of thousands or millions of views) posted in the last 24 hours that are currently trending globally on X (Twitter) in these categories: "Technology", "Business and Finance", and "Cryptocurrency".

For each viral video tweet, I need the exact author's username and a unique key phrase of 5-8 words from the tweet text.

Return ONLY a JSON response in the following format:
{
  "videos": [
    {
      "username": "exact_username_without_at",
      "key_phrase": "a unique contiguous phrase of 5-8 words from the tweet text",
      "views_estimate": 1500000,
      "category": "Technology | Business and Finance | Cryptocurrency",
      "summary": "Short description of the video content"
    }
  ]
}
"""

try:
    print("Asking Grok for viral Explore videos...")
    response = client.chat.completions.create(
        model="grok-3-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a real-time data analyst for X (Twitter) with access to real-time search and Explore categories. Reply ONLY with valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=1000
    )
    
    data = json.loads(response.choices[0].message.content.strip())
    videos = data.get("videos", [])
    print(f"Grok returned {len(videos)} candidates. Bridging with X API...")
    
    verified_tweets = []
    for v in videos:
        username = v["username"]
        key_phrase = v["key_phrase"]
        print(f"  Searching X for: from:{username} \"{key_phrase}\"")
        
        # Build specific search query
        query = f'from:{username} "{key_phrase}"'
        try:
            results = twitter.search_video_tweets(query, max_results=5)
            if results:
                t = results[0]
                real_views = t["public_metrics"].get("impression_count", 0)
                print(f"    ✅ Found Real Tweet! ID: {t['id']} | Views (API): {real_views} | Text: {t['text'][:60]}...")
                verified_tweets.append({
                    "id": t["id"],
                    "username": t["username"],
                    "text": t["text"],
                    "views": real_views,
                    "likes": t["public_metrics"].get("like_count", 0),
                    "summary": v["summary"]
                })
            else:
                print(f"    ❌ No matching tweet found on X.")
        except Exception as e:
            print(f"    ❌ Error searching X: {e}")
            
    print(f"\nSuccessfully Verified {len(verified_tweets)} Real Tweets:")
    verified_tweets.sort(key=lambda x: x["views"], reverse=True)
    for idx, vt in enumerate(verified_tweets):
        print(f"  [{idx}] by @{vt['username']} | Real Views: {vt['views']} | ID: {vt['id']} | Text: {vt['text'][:80]}...")
        
except Exception as e:
    print(f"Error: {e}")
