import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()

from config.settings import settings

print("Testing Grok API search capabilities...")

# Let's try calling with tools on /chat/completions first
url = f"{settings.GROK_BASE_URL}/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {settings.GROK_API_KEY}"
}

payload = {
    "model": "grok-3-mini",
    "messages": [
        {"role": "user", "content": "What is the latest news about SpaceX acquiring Cursor? Did SpaceX buy Cursor recently? Tell me the details."}
    ],
    "tools": [{"type": "web_search"}]
}

try:
    print("\nTrying /chat/completions with web_search tool...")
    response = requests.post(url, headers=headers, json=payload)
    print("Status Code:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print("Response content:")
        print(data["choices"][0]["message"]["content"])
    else:
        print("Error response:", response.text)
except Exception as e:
    print("Exception on /chat/completions:", e)

# Let's try /responses endpoint if the above failed or just to test it
url_responses = f"{settings.GROK_BASE_URL}/responses"
payload_responses = {
    "model": "grok-3-mini",
    "input": [
        {"role": "user", "content": "What is the latest news about SpaceX acquiring Cursor? Did SpaceX buy Cursor recently? Tell me the details."}
    ],
    "tools": [{"type": "web_search"}]
}

try:
    print("\nTrying /responses with web_search tool...")
    response = requests.post(url_responses, headers=headers, json=payload_responses)
    print("Status Code:", response.status_code)
    if response.status_code == 200:
        print("Response content:")
        print(response.json())
    else:
        print("Error response:", response.text)
except Exception as e:
    print("Exception on /responses:", e)

# Let's also test a plain request without tools but asking a direct question to see if it has cut-off knowledge
payload_plain = {
    "model": "grok-3-mini",
    "messages": [
        {"role": "user", "content": "Did SpaceX acquire Cursor recently for 60 billion? If yes, when was it announced?"}
    ]
}
try:
    print("\nTrying plain /chat/completions request without tools...")
    response = requests.post(url, headers=headers, json=payload_plain)
    print("Status Code:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print("Response content:")
        print(data["choices"][0]["message"]["content"])
    else:
        print("Error response:", response.text)
except Exception as e:
    print("Exception on plain request:", e)
