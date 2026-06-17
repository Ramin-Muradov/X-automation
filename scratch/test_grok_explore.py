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
Analyze the X (Twitter) Explore/Trending section globally. Focus on these specific categories: "Technology", "Business and Finance", and "Cryptocurrency".
Find 5 of the most viral, highly viewed video tweets (videos with hundreds of thousands or millions of views) posted in the last 24 hours within these categories.

For each viral video tweet, I need the exact author's username and the exact status ID (tweet ID) so we can quote-tweet it.

Return ONLY a JSON response in the following format:
{
  "videos": [
    {
      "username": "exact_username_without_at",
      "tweet_id": "exact_status_id_string",
      "views": 1200000,
      "category": "Technology | Business and Finance | Cryptocurrency",
      "summary": "Short 1-sentence description of the video content"
    }
  ]
}
"""

try:
    response = client.chat.completions.create(
        model="grok-3-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a real-time data analyst for X (Twitter). You have access to X real-time data, trending topics, and explore categories. Reply ONLY with valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=1000
    )
    
    print("Grok Raw Response:")
    print(response.choices[0].message.content.strip())
except Exception as e:
    print(f"Error: {e}")
