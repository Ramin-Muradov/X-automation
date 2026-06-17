"""
X Automation — Grok (xAI) Trend Finder
Uses xAI's Grok API (grok-3 model) to find the last 24 hours'
trending topics in Business, Startups & Finance and returns
a structured JSON summary for DeepSeek to act on.
"""

import json
import requests
from datetime import datetime, timezone

from openai import OpenAI  # xAI Grok uses an OpenAI-compatible endpoint

from config.settings import settings
from src.logger import setup_logger

logger = setup_logger(__name__, settings.LOGS_DIR / "automation.log", settings.LOG_LEVEL)

# grok-3-mini: 10-30x cheaper than grok-3, sufficient for trend analysis
# Input: $0.30/1M tokens | Output: $0.50/1M tokens
# (grok-3 would be $3.00/$15.00 — overkill for this task)
GROK_MODEL = "grok-3-mini"


class GrokTrendFinder:
    """Finds trending topics from the last 24 hours and returns a JSON summary."""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.GROK_API_KEY,
            base_url=settings.GROK_BASE_URL,
        )
        logger.info("✅ Grok (xAI) client ready.")

    def _build_prompt(self) -> str:
        """Builds the trend-search prompt sent to Grok."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        niche = settings.BUSINESS_NICHE

        return f"""
Current time: {now}

Task: Find the 5-7 most significant trending topics in "{niche}" from the last 24 hours.

For each trend provide:
1. trend_title   – Short name of the trend
2. summary       – What it is about (2-3 sentences)
3. why_trending  – Why it is trending right now
4. key_facts     – The single most important number or fact (if available)
5. x_discussion  – What angle is being actively discussed on X (Twitter)
6. content_angle – The most interesting perspective for writing a post about this

Reply ONLY with the following JSON, nothing else:

{{
  "analysis_time": "{now}",
  "niche": "{niche}",
  "trends": [
    {{
      "trend_title": "...",
      "summary": "...",
      "why_trending": "...",
      "key_facts": "...",
      "x_discussion": "...",
      "content_angle": "..."
    }}
  ]
}}
"""

    def find_trends(self) -> dict:
        """
        Calls the Grok API and returns structured trend data.

        Returns:
            {
              "analysis_time": str,
              "niche": str,
              "trends": [ {trend_title, summary, ...}, ... ]
            }

        Raises:
            RuntimeError: on API error or JSON parse failure
        """
        logger.info(f"🔍 Grok trend search starting — Niche: [{settings.BUSINESS_NICHE}]")

        url = f"{settings.GROK_BASE_URL}/responses"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.GROK_API_KEY}"
        }

        payload = {
            "model": GROK_MODEL,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert analyst in business, startups, and finance. "
                        "You have real-time knowledge of current events and trending topics. "
                        "Always reply with clean, valid JSON only."
                    ),
                },
                {"role": "user", "content": self._build_prompt()},
            ],
            "tools": [{"type": "web_search"}],
            "temperature": 0.2,
            "max_output_tokens": 2048
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            res_data = response.json()

            raw = ""
            for item in res_data.get("output", []):
                if item.get("type") == "message" and item.get("role") == "assistant":
                    for content_item in item.get("content", []):
                        if content_item.get("type") == "output_text":
                            raw = content_item.get("text", "").strip()
                            break

            if not raw:
                raise RuntimeError("No assistant message found in Grok responses API output")

        except Exception as e:
            logger.error(f"❌ Grok API Responses Call Error: {e}")
            raise RuntimeError(f"Grok API call failed: {e}") from e

        logger.debug(f"Grok raw response (first 300 chars):\n{raw[:300]}")

        trend_data = self._parse_json(raw)

        count = len(trend_data.get("trends", []))
        logger.info(f"✅ {count} trends found:")
        for i, t in enumerate(trend_data.get("trends", []), 1):
            logger.info(f"   {i}. {t.get('trend_title', 'N/A')}")

        return trend_data

    def _parse_json(self, raw: str) -> dict:
        """Strips markdown fences if present, then parses JSON."""
        if "```" in raw:
            lines = raw.split("\n")
            raw = "\n".join(
                l for l in lines if not l.strip().startswith("```")
            ).strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error: {e}\nReceived text: {raw[:200]}")
            raise RuntimeError(f"Grok response is not valid JSON: {e}") from e

    def get_trend_summary_text(self, trend_data: dict) -> str:
        """
        Converts the trend dict into a readable text block
        to send to DeepSeek.

        Args:
            trend_data: dict returned by find_trends()

        Returns:
            Formatted multi-line string
        """
        lines = [
            f"📊 TREND ANALYSIS — {trend_data.get('niche', '')}",
            f"⏰ Time: {trend_data.get('analysis_time', '')}",
            "",
        ]

        for i, t in enumerate(trend_data.get("trends", []), 1):
            lines += [
                "─" * 50,
                f"#{i} {t.get('trend_title', '')}",
                f"📌 What: {t.get('summary', '')}",
                f"🔥 Why trending: {t.get('why_trending', '')}",
                f"📈 Key fact: {t.get('key_facts', 'N/A')}",
                f"🐦 X discussion: {t.get('x_discussion', '')}",
                f"💡 Content angle: {t.get('content_angle', '')}",
                "",
            ]

        return "\n".join(lines)

    def get_influential_accounts(self) -> list[str]:
        """
        Uses Grok to dynamically find the top 20 most influential personalities 
        and organizations on X for the configured business niche.
        """
        logger.info(f"🔮 Grok dynamically fetching top X accounts for niche: [{settings.BUSINESS_NICHE}]")
        
        fallback = ["business", "Bloomberg", "WSJ", "TechCrunch", "YCombinator", "ElonMusk", "BillGates", "paulg", "FT", "Forbes"]
        
        try:
            response = self.client.chat.completions.create(
                model=GROK_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Always reply with the exact requested format and no other text."
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Provide a comma-separated list of the 50 most active and influential X (Twitter) usernames (without @) "
                            f"whose video tweets frequently trend globally under the Explore categories 'Technology', 'Business and Finance', and 'Cryptocurrency'. "
                            f"Include major tech/business news brands, tech leaders/CEOs, VCs, top founders, and curators. "
                            f"Strictly avoid general/global news agencies like Reuters, AP, AFP, BBC, or CNN. "
                            f"Return ONLY the usernames separated by commas, nothing else."
                        )
                    }
                ],
                temperature=0.2,
                max_tokens=600
            )
            
            raw = response.choices[0].message.content.strip()
            # Clean and parse comma-separated list
            accounts = [acc.strip() for acc in raw.split(",") if acc.strip() and not acc.strip().startswith("@")]
            # Filter out any weird text in case Grok returned extra content
            clean_accounts = []
            for acc in accounts[:65]:
                # Username should be alphanumeric + underscores, 1 to 15 chars
                clean_acc = "".join(c for c in acc if c.isalnum() or c == "_")
                if 1 <= len(clean_acc) <= 15:
                    clean_accounts.append(clean_acc)
            
            if clean_accounts:
                logger.info(f"   Successfully fetched {len(clean_accounts)} dynamic accounts from Grok.")
                return clean_accounts
            
            logger.warning("⚠️ Grok returned empty or invalid usernames. Using fallback list.")
            return fallback
            
        except Exception as e:
            logger.error(f"❌ Error getting dynamic accounts from Grok: {e}. Using fallback list.")
            return fallback

