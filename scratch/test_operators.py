import os
from dotenv import load_dotenv
load_dotenv()

from src.twitter_client import TwitterClient

client = TwitterClient()

operators = [
    'has:videos ("business" OR "finance" OR "tech") min_retweets:5',
    'has:videos ("business" OR "finance" OR "tech") min_replies:5',
    'has:videos ("business" OR "finance" OR "tech") min_faves:5'
]

for op in operators:
    print(f"Testing operator query: {op}")
    try:
        results = client.search_video_tweets(op, max_results=5)
        print(f"  Success! Found {len(results)} results.")
    except Exception as e:
        print(f"  Failed: {e}")
