import os
from dotenv import load_dotenv
load_dotenv()

import tweepy
from src.twitter_client import TwitterClient

client = TwitterClient()

tweet_id = "2061105168092164432"
print(f"Fetching details for tweet ID: {tweet_id}...")

try:
    # Use API v2 to get the tweet
    response = client.client_v2.get_tweet(
        id=tweet_id,
        tweet_fields=["public_metrics", "created_at", "entities", "attachments", "author_id", "text"],
        expansions=["author_id"],
        user_fields=["public_metrics", "verified"]
    )
    
    if response.data:
        t = response.data
        print(f"Text: {t.text}")
        print(f"Created At: {t.created_at}")
        print(f"Metrics: {t.public_metrics}")
        
        user_info = None
        if response.includes and "users" in response.includes:
            user_info = response.includes["users"][0]
            print(f"Author Username: @{user_info.username}")
            print(f"Author Followers: {user_info.public_metrics.get('followers_count', 0)}")
            print(f"Author Verified: {getattr(user_info, 'verified', False)}")
    else:
        print("No tweet data returned.")
        
except Exception as e:
    print(f"Error fetching tweet: {e}")
