import os
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from config.settings import settings

client = OpenAI(
    api_key=settings.GROK_API_KEY,
    base_url=settings.GROK_BASE_URL,
)

prompt = """
Please browse X (Twitter) and look at the real-time Global Explore / Trending tab. Focus on the three categories: "Technology", "Business and Finance", and "Cryptocurrency".
Find 3-5 of the absolute most viewed video tweets posted in the last 24 hours in these categories.
For each tweet, list the real, actual tweet URL, the username, the view count, and a short description.
Double check that the tweet URLs and status IDs are real and exist on X. Do not make up or guess any IDs.
"""

print("Querying Grok for real-time trending video tweets...")
try:
    response = client.chat.completions.create(
        model="grok-3-mini",
        messages=[
            {"role": "system", "content": "You are a real-time data analyst for X (Twitter). You search and report real, actual trending tweets on X with real URLs."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    print("\n--- Grok Response ---")
    print(response.choices[0].message.content)
    print("---------------------")
except Exception as e:
    print(f"Error: {e}")
