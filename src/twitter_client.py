"""
X Automation — Twitter Client
tweepy vasitəsilə X API v2 ilə əlaqəni idarə edir.
Tək post + Thread dəstəyi var.
"""

import time

import tweepy

from config.settings import settings
from src.logger import setup_logger

logger = setup_logger(__name__, settings.LOGS_DIR / "automation.log", settings.LOG_LEVEL)

# Thread tweet-ləri arasındakı fasilə (saniyə)
THREAD_DELAY_SECONDS = 2


class TwitterClient:
    """X (Twitter) API ilə bütün əməliyyatları idarə edir."""

    def __init__(self):
        # ── API v2 (tweet göndərmək üçün) ────────────────────────────────────
        self.client_v2 = tweepy.Client(
            consumer_key=settings.X_API_KEY,
            consumer_secret=settings.X_API_SECRET,
            access_token=settings.X_ACCESS_TOKEN,
            access_token_secret=settings.X_ACCESS_TOKEN_SECRET,
            bearer_token=settings.X_BEARER_TOKEN,
            wait_on_rate_limit=True,
        )

        # ── API v1.1 (media yükləmək üçün) ───────────────────────────────────
        auth = tweepy.OAuth1UserHandler(
            consumer_key=settings.X_API_KEY,
            consumer_secret=settings.X_API_SECRET,
            access_token=settings.X_ACCESS_TOKEN,
            access_token_secret=settings.X_ACCESS_TOKEN_SECRET,
        )
        self.api_v1 = tweepy.API(auth, wait_on_rate_limit=True)

        logger.info("✅ X API klienti hazırdır.")

    # ─────────────────────────────────────────────────────────────────────────
    # Tək post
    # ─────────────────────────────────────────────────────────────────────────

    def post_tweet(
        self,
        text: str,
        media_ids: list[str] | None = None,
        reply_to_id: str | None = None,
        quote_tweet_id: str | None = None,
    ) -> dict:
        """
        X platformasına tək post göndərir.

        Args:
            text:           Post mətni (maks. 280 simvol)
            media_ids:      Yüklənmiş media ID-ləri (istəyə bağlı)
            reply_to_id:    Cavab veriləcək tweet ID-si (thread üçün)
            quote_tweet_id: Sitat gətiriləcək tweet ID-si (quote tweet üçün)

        Returns:
            {"success": bool, "tweet_id": str | None, "error": str | None}
        """
        if settings.DRY_RUN:
            log_prefix = ""
            if reply_to_id:
                log_prefix = " ↳ reply"
            elif quote_tweet_id:
                log_prefix = f" ↳ quote of {quote_tweet_id}"
            logger.info(f"🧪 [TEST] Tweet{log_prefix}: {text[:80]}...")
            return {"success": True, "tweet_id": f"DRY_{hash(text) % 99999}", "error": None}

        try:
            kwargs: dict = {"text": text}
            if media_ids:
                kwargs["media_ids"] = media_ids
            if reply_to_id:
                kwargs["in_reply_to_tweet_id"] = reply_to_id
            if quote_tweet_id:
                kwargs["quote_tweet_id"] = quote_tweet_id

            response = self.client_v2.create_tweet(**kwargs)
            tweet_id = str(response.data["id"])
            return {"success": True, "tweet_id": tweet_id, "error": None}

        except tweepy.TweepyException as e:
            logger.error(f"❌ Tweet göndərmə xətası: {e}")
            return {"success": False, "tweet_id": None, "error": str(e)}

    def search_video_tweets(self, query: str, start_time: str | None = None, max_results: int = 50, sort_order: str = "relevancy") -> list:
        """
        X API v2 vasitəsilə son video postları axtarır.

        Args:
            query:       Axtarış sorğusu
            start_time:  Axtarışın başlanğıc zamanı (ISO 8601 UTC timestamp formatında)
            max_results: Qaytarılacaq maksimum nəticə sayı (10-100)
            sort_order:  Sıralama qaydası ('relevancy' və ya 'recency')

        Returns:
            list[dict]
        """
        try:
            max_results = max(10, min(100, max_results))
            logger.info(f"🔍 X API vasitəsilə video postları axtarılır: '{query}' (limit: {max_results}, sort: {sort_order})")
            
            kwargs = {
                "query": query,
                "max_results": max_results,
                "sort_order": sort_order,
                "tweet_fields": ["public_metrics", "created_at", "entities", "attachments", "author_id"],
                "expansions": ["author_id"],
                "user_fields": ["public_metrics", "verified"]
            }
            if start_time:
                kwargs["start_time"] = start_time
                logger.info(f"   Axtarışın başlanğıc zamanı: {start_time}")
                
            response = self.client_v2.search_recent_tweets(**kwargs)
            
            user_map = {}
            if response.includes and "users" in response.includes:
                for u in response.includes["users"]:
                    followers = 0
                    if u.public_metrics and "followers_count" in u.public_metrics:
                        followers = u.public_metrics["followers_count"]
                    user_map[u.id] = {
                        "username": u.username,
                        "followers_count": followers,
                        "verified": getattr(u, "verified", False)
                    }

            tweets = []
            if response.data:
                for t in response.data:
                    user_info = user_map.get(t.author_id, {"username": "i", "followers_count": 0, "verified": False})
                    tweets.append({
                        "id": str(t.id),
                        "text": t.text,
                        "public_metrics": t.public_metrics or {},
                        "created_at": t.created_at,
                        "username": user_info["username"],
                        "followers_count": user_info["followers_count"],
                        "verified": user_info["verified"]
                    })
            return tweets
        except tweepy.TweepyException as e:
            logger.error(f"❌ Video tweet axtarışı zamanı xəta yarandı: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Thread göndərilişi
    # ─────────────────────────────────────────────────────────────────────────

    def post_thread(
        self,
        tweets: list[str],
        first_media_ids: list[str] | None = None,
    ) -> dict:
        """
        Thread (bir-birinə bağlı tweet seriyası) göndərir.

        Args:
            tweets:           Tweet mətnlərinin sıralı siyahısı
            first_media_ids:  Yalnız birinci tweete media əlavə et

        Returns:
            {
              "success": bool,
              "thread_ids": [str, ...],
              "first_tweet_id": str | None,
              "error": str | None
            }
        """
        if not tweets:
            return {"success": False, "thread_ids": [], "first_tweet_id": None,
                    "error": "Tweet siyahısı boşdur"}

        logger.info(f"🧵 Thread göndərilir — {len(tweets)} tweet")
        thread_ids: list[str] = []
        parent_id: str | None = None

        for i, text in enumerate(tweets, 1):
            # Yalnız birinci tweete media əlavə et
            media_ids = first_media_ids if (i == 1 and first_media_ids) else None

            result = self.post_tweet(
                text=text,
                media_ids=media_ids,
                reply_to_id=parent_id,
            )

            if not result["success"]:
                logger.error(f"❌ Thread {i}-ci tweet uğursuz: {result['error']}")
                return {
                    "success": False,
                    "thread_ids": thread_ids,
                    "first_tweet_id": thread_ids[0] if thread_ids else None,
                    "error": result["error"],
                }

            tweet_id = result["tweet_id"]
            thread_ids.append(tweet_id)
            parent_id = tweet_id

            logger.info(f"   ✅ Tweet {i}/{len(tweets)} göndərildi — ID: {tweet_id}")

            # Rate limit üçün tweet-lər arasında qısa fasilə
            if i < len(tweets):
                time.sleep(THREAD_DELAY_SECONDS)

        first_id = thread_ids[0] if thread_ids else None
        if not settings.DRY_RUN and first_id:
            logger.info(f"🎉 Thread tamamlandı!")
            logger.info(f"   URL: https://x.com/i/web/status/{first_id}")

        return {
            "success": True,
            "thread_ids": thread_ids,
            "first_tweet_id": first_id,
            "error": None,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Yardımçı metodlar
    # ─────────────────────────────────────────────────────────────────────────

    def verify_credentials(self) -> bool:
        """API bağlantısını yoxlayır."""
        try:
            me = self.client_v2.get_me()
            username = me.data.username
            logger.info(f"✅ X API yoxlaması uğurlu — @{username}")
            return True
        except Exception as e:
            logger.error(f"❌ X API yoxlaması uğursuz: {e}")
            return False
