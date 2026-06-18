"""
X Automation — DeepSeek Məzmun Yazıcısı
Groq-dan gələn trend summaryni oxuyur, ən güclü post ideyasını
seçir, tək post və ya thread kimi yazır.
"""

import json
from dataclasses import dataclass, field
from typing import Literal

from openai import OpenAI  # DeepSeek OpenAI-uyumlu API istifadə edir

from config.settings import settings
from src.logger import setup_logger

logger = setup_logger(__name__, settings.LOGS_DIR / "automation.log", settings.LOG_LEVEL)

DEEPSEEK_MODEL = "deepseek-reasoner"
PostType = Literal["single", "thread"]


@dataclass
class PostContent:
    """DeepSeek-in yaratdığı post məzmunu."""
    post_type: PostType
    tweets: list[str]          # Tək post üçün 1 element, thread üçün 3-5
    chosen_trend: str          # Seçilmiş trendin adı
    reasoning: str             # DeepSeek-in seçim səbəbi
    image_prompt: str          # Şəkil yaratmaq üçün prompt
    has_image: bool            # Şəkil əlavə edilsin ya yox
    stance_summary: str        # Postun əsas tezisləri / məntiqi xülasəsi (contradiction-ların qarşısını almaq üçün)

    @property
    def is_thread(self) -> bool:
        return self.post_type == "thread"

    @property
    def tweet_count(self) -> int:
        return len(self.tweets)


class DeepSeekWriter:
    """Trend analizini alıb X postu/thread yaradır."""

    def __init__(self):
        # DeepSeek OpenAI-uyumlu API endpoint istifadə edir
        self.client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        logger.info("✅ DeepSeek klienti hazırdır.")

    # ─────────────────────────────────────────────────────────────────────────
    # Mərhələ 1: Trend seçimi və post format qərarı
    # ─────────────────────────────────────────────────────────────────────────

    def _format_recent_posts(self, recent_posts: list[dict] = None) -> str:
        """Tarixçədəki son postların və onların əsas iddialarının/mövqelərinin (stance) xülasəsini hazırlayır."""
        if not recent_posts:
            return "Heç bir son post yoxdur (tarixçə boşdur)."
        lines = []
        for i, post in enumerate(recent_posts, 1):
            trend = post.get("chosen_trend", "Naməlum")
            stance = post.get("stance_summary")
            if not stance:
                # Əgər əvvəlki yazılarda stance_summary yoxdursa, ilk tweetin bir hissəsini fallback kimi götürürük
                tweets = post.get("tweets", [])
                first_tweet = tweets[0] if tweets else ""
                stance = f"First tweet hook: {first_tweet[:120]}..."
            lines.append(f"{i}. Trend: {trend} | Stance: {stance}")
        return "\n".join(lines)

    def _decide_content_strategy(self, trend_summary: str, recent_posts: list[dict] = None) -> dict:
        """
        Sends the trend summary to DeepSeek and asks it to decide
        which trend to pick and whether to write a single post or a thread.
        """
        system_msg = """You are a viral X (Twitter) content strategist and writer.
Your job:
1. From the given trend list, pick the single strongest, most engaging topic with the absolute highest virality potential.
2. Decide whether it fits in a single tweet or needs a thread.
3. Explain your reasoning.
4. Write a descriptive prompt for generating a high-quality, professional, realistic, topic-specific photo or clean 3D illustration image that represents this trend (e.g. if talking about Tesla, describe a high-tech Tesla car; if about Bitcoin, a golden Bitcoin coin on a dark reflective surface). It must NOT contain any text, words, labels, or UI overlays.
5. Decide if adding a generated image would significantly improve the visual appeal and quality/virality of the post. Set "has_image" to true if a picture makes sense for the topic; set it to false if the post is better suited for a text-only format.

RULE — Post type decision:
- "single": The idea can be expressed powerfully within 280 characters
- "thread": The idea is complex, has steps, numbers, or a list that deserves more space

STRICT RULE — Consistency and Non-Contradiction:
Do NOT select a trend, take a stance, or present arguments that contradict or repeat the stances and logical viewpoints in the recent posts history. Keep the narrative, opinions, and viewpoint strictly consistent. For example, if a previous post argued that a technology is a major breakthrough, a new post must not claim it is useless or a fad.

STRICT RULE — Subject Variety:
Do NOT select a trend that focuses on the same company, product, or specific core subject (e.g. SpaceX, Tesla, Stripe, Bitcoin, Nvidia) that was already covered in the recent posts history. We must maintain diversity of subjects on the timeline. If the top trend is a repetition of a recently covered company or topic, select the next strongest, non-repeating trend from the list.

Reply ONLY in JSON:
{
  "chosen_trend": "name of the chosen trend",
  "post_type": "single" OR "thread",
  "reasoning": "why you chose this trend and this post type",
  "core_idea": "the core angle/perspective you will build the post around",
  "image_prompt": "a highly descriptive image generation prompt, strictly without any text or overlays in the image description",
  "has_image": true OR false
}"""

        history_text = self._format_recent_posts(recent_posts)
        user_msg = f"""Review the following trend analysis and determine the strategy:

{trend_summary}

Recent posts history (do NOT contradict or repeat these, maintain consistency):
{history_text}

Select the most viral topic, ensure it is consistent with past posts, and decide on the post type."""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=8192,
        )

        raw = response.choices[0].message.content.strip()
        strategy = self._parse_json(raw, step="strategy")

        logger.info(f"🧠 DeepSeek strategiyası:")
        logger.info(f"   Seçilmiş trend: {strategy.get('chosen_trend')}")
        logger.info(f"   Post tipi: {strategy.get('post_type', '').upper()}")
        logger.info(f"   Səbəb: {strategy.get('reasoning', '')[:80]}...")

        return strategy

    # ─────────────────────────────────────────────────────────────────────────
    # Mərhələ 2: Məzmunun yazılması
    # ─────────────────────────────────────────────────────────────────────────

    def _write_single_post(self, strategy: dict, trend_summary: str, recent_posts: list[dict] = None) -> tuple[list[str], str]:
        """Writes a single tweet (≤280 characters) and returns the tweet and the stance summary."""
        system_msg = f"""You are an expert at writing highly engaging, realistic, and viral X (Twitter) posts.

STRICT RULES:
- Write in {settings.POST_LANGUAGE}
- Extremely strict limit: The entire tweet must be MAXIMUM 240 characters (including hashtags and emojis) so it never gets truncated or cut off.
- Do NOT give direct advice, lessons, or coaching tips to the reader (avoid coaching phrases like "Founders take note", "Always remember", "My advice is", "Here is a lesson", etc.). Maintain an objective, analytical, or narrative tone.
- Add 2-4 relevant hashtags
- Use 1-3 emojis placed naturally (not at the very start)
- Provide a clear, brief explanation or insight about the trend. Don't just announce the topic; explain the "why" or "how" (the underlying mechanism or reason) so the reader gets actual value and explanation from the post.
- Make it extremely interesting, thought-provoking, and realistic. It should reflect reality to captivate and hook the audience.
- Do NOT include any placeholder accounts, usernames, links, or tag handles (e.g., do NOT tag other accounts or write placeholders like "@yourhandle").
- No promotional language
- Consistency rule: Do NOT write arguments or facts that contradict any of the recent posts in the history. Maintain a logical and consistent stance.
- Reply ONLY in JSON:
{{
  "tweet": "The written tweet content here",
  "stance_summary": "A concise, 1-sentence summary of the main claim, belief, or viewpoint asserted in this tweet (e.g., 'Asserted that Stripe Treasury 2.0 is superior to traditional business banking for startups due to 5.1% yield')"
}}"""

        history_text = self._format_recent_posts(recent_posts)
        user_msg = f"""Write a tweet based on this strategy:

Chosen trend: {strategy.get('chosen_trend')}
Core idea: {strategy.get('core_idea')}

Recent posts history (do NOT contradict or repeat these, maintain consistency):
{history_text}

Context from trend analysis:
{trend_summary[:1000]}"""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=8192,
        )

        raw = response.choices[0].message.content.strip()
        data = self._parse_json(raw, step="single_post")
        tweet = data.get("tweet", "").strip()
        stance_summary = data.get("stance_summary", "").strip()

        # 280 simvol həddini yoxla
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
            logger.warning("⚠️  Tweet 280 simvolu keçdi, kəsildi.")

        logger.info(f"✍️  Tək post hazır ({len(tweet)} simvol)")
        return [tweet], stance_summary

    def _write_thread(self, strategy: dict, trend_summary: str, recent_posts: list[dict] = None) -> tuple[list[str], str]:
        """Writes a thread of 3-5 tweets and returns the tweets and the stance summary."""
        system_msg = f"""You are an expert at writing viral, realistic, and highly engaging X (Twitter) threads.

STRICT RULES:
- Write in {settings.POST_LANGUAGE}
- Each tweet: MAXIMUM 240 characters (strictly enforce this limit so no tweet is truncated or cut off)
- Between 3 and 5 tweets (keep it tight)
- Do NOT give direct advice, lessons, or coaching tips to the reader (avoid phrases like "Founders take note", "Always remember", "My advice is", "Here is a lesson", etc.). Maintain an objective, analytical, or narrative tone.
- Make sure the thread provides clear educational value, explaining the mechanics, reasons, or details of the trend step-by-step so it serves as a clear explanation of the topic.
- Make the content extremely interesting, reflecting real-world situations, data, or facts to maximize engagement.
- First tweet: The hook — must make readers stop scrolling and read on. Do NOT add any sequence number or prefix (like "1/N", "(1/N)" or "1/") to the first tweet. Start directly with the content.
- Subsequent tweets (from the second tweet onwards): Start each tweet with its sequence number: "2/N", "3/N" ... "N/N" (where N is the total tweet count).
- Last tweet: Clear call to action (like asking the readers to reply with their take or share). DO NOT include any placeholder usernames, handles, or links (do NOT write "@yourhandle", "@username", etc.). Never tag other accounts.
- Consistency rule: Do NOT write arguments or facts that contradict any of the recent posts in the history. Keep the narrative consistent.
- Logical, flowing structure throughout
- Relevant hashtags mostly in the last tweet
- Reply ONLY in JSON:

{{
  "tweet_count": N,
  "tweets": [
    "first tweet text (DO NOT start with 1/N or 1/)",
    "2/N second tweet text",
    "3/N third tweet text",
    ...
  ],
  "stance_summary": "A concise, 1-sentence summary of the overall viewpoint and main claims made in this thread (e.g., 'Argued that the AI chip export ban requires hardware pivots like AMD/Intel or spot-instance models')"
}}"""

        history_text = self._format_recent_posts(recent_posts)
        user_msg = f"""Write a thread based on this strategy:

Chosen trend: {strategy.get('chosen_trend')}
Core idea: {strategy.get('core_idea')}

Recent posts history (do NOT contradict or repeat these, maintain consistency):
{history_text}

Context:
{trend_summary[:1500]}"""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=8192,
        )

        raw = response.choices[0].message.content.strip()
        data = self._parse_json(raw, step="thread")
        tweets = data.get("tweets", [])
        stance_summary = data.get("stance_summary", "").strip()

        # Hər tweetin uzunluğunu yoxla
        validated = []
        for i, tw in enumerate(tweets, 1):
            if len(tw) > 280:
                tw = tw[:277] + "..."
                logger.warning(f"⚠️  Thread {i}-ci tweet 280 simvolu keçdi, kəsildi.")
            validated.append(tw)

        logger.info(f"✍️  Thread hazır — {len(validated)} tweet")
        for i, tw in enumerate(validated, 1):
            logger.info(f"   [{i}] ({len(tw)} simvol): {tw[:50]}...")

        return validated, stance_summary

    # ─────────────────────────────────────────────────────────────────────────
    # Əsas ictimai metod
    # ─────────────────────────────────────────────────────────────────────────

    def create_post(self, trend_summary: str, recent_posts: list[dict] = None) -> PostContent:
        """
        Trend summaryni alıb tam post məzmunu yaradır.

        Args:
            trend_summary: Output from GroqTrendFinder.get_trend_summary_text()
            recent_posts: Tarixçədəki son postlar listi

        Returns:
            PostContent dataclass instance
        """
        logger.info("📝 DeepSeek content generation starting...")

        # Stage 1: Strategy decision
        strategy = self._decide_content_strategy(trend_summary, recent_posts=recent_posts)
        post_type: PostType = strategy.get("post_type", "single")

        # Stage 2: Content writing
        if post_type == "thread":
            logger.info("🧵 Writing thread...")
            tweets, stance_summary = self._write_thread(strategy, trend_summary, recent_posts=recent_posts)
        else:
            logger.info("📄 Writing single post...")
            tweets, stance_summary = self._write_single_post(strategy, trend_summary, recent_posts=recent_posts)

        return PostContent(
            post_type=post_type,
            tweets=tweets,
            chosen_trend=strategy.get("chosen_trend", ""),
            reasoning=strategy.get("reasoning", ""),
            image_prompt=strategy.get("image_prompt", f"A clean professional illustration of {strategy.get('chosen_trend', 'technology trend')}"),
            has_image=bool(strategy.get("has_image", True)),
            stance_summary=stance_summary,
        )

    def create_video_comment(self, original_tweet_text: str) -> str:
        """
        Giriş olaraq video tweet-in mətnini alır və DeepSeek vasitəsilə 1-2 cümləlik viral,
        izah edici/məlumat verici şərh (quote tweet mətni) hazırlayır.
        """
        logger.info("📝 DeepSeek video şərhi yaradır...")
        
        system_msg = f"""You are a professional social media manager and viral content creator on X (Twitter).
Your task is to write a highly engaging, professional, and informative 1-2 sentence comment or explanation about a video tweet.

STRICT RULES:
- Write in {settings.POST_LANGUAGE} (must write in this language).
- Maximum length is 240 characters (strictly enforce this so the post does not get truncated).
- Make it 1-2 sentences only. Be concise, direct, and insightful.
- Do NOT tag any other accounts or include any usernames/handles (e.g. do not write @username).
- Do NOT add placeholders.
- Add 1-2 relevant hashtags.
- Use 1 emoji placed naturally if it improves the post.
- Focus on explaining the value, significance, or key insight shown in the video content.
- Reply ONLY with the final text of your comment, no JSON formatting, no quotes around the text, no conversational text, and no markdown formatting."""

        user_msg = f"""Here is the text of the video tweet we are commenting on:
---
{original_tweet_text}
---

Generate the 1-2 sentence comment/explanation for X now:"""

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        comment = response.choices[0].message.content.strip()
        
        # Clean up quotes if DeepSeek wrapped the response in quotes
        if comment.startswith('"') and comment.endswith('"'):
            comment = comment[1:-1].strip()
        elif comment.startswith("'") and comment.endswith("'"):
            comment = comment[1:-1].strip()

        # Enforce 280 character limit
        if len(comment) > 280:
            comment = comment[:277] + "..."
            logger.warning("⚠️  Generated comment exceeded 280 characters, it was truncated.")
            
        logger.info(f"✍️  Generated video comment: '{comment}'")
        return comment

    def verify_video_relevance(self, candidates: list[dict], recent_posts: list[dict] = None) -> int | None:
        """
        Sends the top video tweet candidates to DeepSeek and asks it to select the single
        most professional, serious, and highly relevant tweet about business, startups, or finance.
        It discards unrelated content like movies, entertainment, memes, or spam.
        
        Args:
            candidates: list of tweet dicts (containing 'id', 'text', 'username')
            recent_posts: list of recent post history to enforce subject variety
            
        Returns:
            The index (0-based) of the selected tweet, or None if no candidate is relevant.
        """
        if not candidates:
            return None
            
        logger.info(f"🧠 DeepSeek {len(candidates)} namizəd video postu ciddi mövzu üçün yoxlayır...")
        
        system_msg = f"""You are a strict editorial curator for a premium, highly professional X (Twitter) account focused on business, startups, and finance.
Your goal is to evaluate candidate tweets containing videos and identify the single most professional, serious, and relevant post.

STRICT CRITERIA:
- The CORE subject of the video and tweet MUST be strictly about serious business, startup companies, corporate finance, venture capital, fintech, tech industries, market trends, economic data, or corporate strategy/management.
- You MUST reject: general science, wildlife, nature, climate change, travel blogs, local news, crime, geopolitics, wars, lifestyle, sports, or entertainment—even if the post mentions a company name (e.g. "Club Med opening a resort") or uses business terms superficially. If the video is mostly about wildlife (like tagging sharks), science, or sports, it is NOT relevant.
- The video must contain actual value for a professional audience: founder/CEO interviews, financial analysis, market discussions, management strategies, or tech innovations.
- Note: The candidates list is sorted in descending order of popularity and views (Candidate Index 0 has the highest views, Index 1 is next, etc.).
- You MUST select the candidate with the HIGHEST views (closest to Index 0) that fully satisfies these strict criteria. Only skip a higher-ranked candidate if it fails these criteria.

STRICT RULE — Subject Variety:
Do NOT select a video tweet that focuses on the same company, product, or specific core subject (e.g. SpaceX, Tesla, Stripe, Bitcoin, Nvidia) that was already covered in the recent posts history. We must maintain diversity of subjects on the timeline. If a high-ranked candidate is a repetition of a recently covered company or topic, skip it and select the next best non-repeating candidate.

Return your decision in the following JSON format:
{{
  "selected_index": integer (0-based index of the chosen tweet from the list, or -1 if none of the candidates are relevant/professional/diverse),
  "reason": "a brief 1-sentence reason for choosing this candidate or rejecting all"
}}
Reply ONLY with the raw JSON, no markdown formatting, no code blocks."""

        history_text = self._format_recent_posts(recent_posts)

        # Format candidates for the prompt
        candidates_text = []
        for idx, c in enumerate(candidates):
            candidates_text.append(f"""Candidate Index: {idx}
Author: @{c['username']}
Tweet Text: {c['text']}
---""")
        
        user_msg = f"""Recent posts history (do NOT select videos about these topics/companies):
{history_text}

Here are the candidate video tweets to evaluate:

{"\n".join(candidates_text)}"""
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1, # very low temp for strict deterministic categorization
                max_tokens=500,
            )
            
            raw = response.choices[0].message.content.strip()
            data = self._parse_json(raw, step="verify_relevance")
            
            selected_idx = data.get("selected_index", -1)
            reason = data.get("reason", "No reason provided")
            
            if selected_idx >= 0 and selected_idx < len(candidates):
                logger.info(f"   ✅ DeepSeek selected candidate {selected_idx}: {reason}")
                return selected_idx
            else:
                logger.warning(f"   ❌ DeepSeek rejected all candidates as irrelevant: {reason}")
                return None
        except Exception as e:
            logger.error(f"❌ Error during DeepSeek relevance validation: {e}")
            return None

    def _parse_json(self, raw: str, step: str = "") -> dict:
        """Markdown kod bloklarını sıyırıb JSON parse edir."""
        if "```" in raw:
            lines = raw.split("\n")
            raw = "\n".join(
                l for l in lines if not l.strip().startswith("```")
            ).strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"❌ [{step}] JSON parse xətası: {e}\nMətn: {raw[:200]}")
            raise RuntimeError(f"DeepSeek [{step}] cavabı JSON formatında deyil: {e}") from e
