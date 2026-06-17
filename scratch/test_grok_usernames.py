import os
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from config.settings import settings

client = OpenAI(
    api_key=settings.GROK_API_KEY,
    base_url=settings.GROK_BASE_URL,
)

response = client.chat.completions.create(
    model="grok-3-mini",
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant. Always reply with the exact requested format and no other text."
        },
        {
            "role": "user",
            "content": "Provide a comma-separated list of the 30 most influential X (Twitter) usernames (without @) of people and organizations in business, technology, startups, and finance who frequently post video clips (e.g., Elon Musk, Bill Gates, major news, tech leaders, VCs). Return ONLY the usernames separated by commas, nothing else."
        }
    ],
    temperature=0.2,
    max_tokens=300
)

print("Grok Response:")
print(response.choices[0].message.content.strip())
