"""
X Automation — Post Manager
Orchestrates the full pipeline:
Grok (trends) → DeepSeek (content) → Media → X (post/thread)
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config.settings import settings
from src.groq_trend_finder import GrokTrendFinder
from src.deepseek_writer import DeepSeekWriter, PostContent
from src.twitter_client import TwitterClient
from src.media_handler import MediaHandler
from src.logger import setup_logger

logger = setup_logger(__name__, settings.LOGS_DIR / "automation.log", settings.LOG_LEVEL)


class PostManager:
    """Orchestrates the full Grok → DeepSeek → X automation pipeline."""

    def __init__(self):
        self.trend_finder = GrokTrendFinder()
        self.writer = DeepSeekWriter()
        self.twitter = TwitterClient()
        self.media_handler = MediaHandler(self.twitter.api_v1)

    # ─────────────────────────────────────────────────────────────────────────
    # Əsas axar
    # ─────────────────────────────────────────────────────────────────────────

    def run(self) -> dict:
        """
        Tam avtomatlaşdırma axarını işə salır.

        Returns:
            {
              "success": bool,
              "post_type": "single" | "thread",
              "chosen_trend": str,
              "tweet_ids": list[str],
              "error": str | None
            }
        """
        run_time = datetime.now(timezone.utc).isoformat()
        logger.info("=" * 60)
        logger.info(f"🚀 Automation pipeline starting — {run_time}")
        logger.info("=" * 60)

        try:
            # ── 1. Grok: Trend analysis ────────────────────────────────────────────
            logger.info("\n[STEP 1/4] 🔍 Grok — Trend search")
            trend_data = self.trend_finder.find_trends()
            trend_summary = self.trend_finder.get_trend_summary_text(trend_data)

            # ── 2. DeepSeek: Content creation ─────────────────────────────────────
            logger.info("\n[STEP 2/4] 🧠 DeepSeek — Content creation")
            recent_posts = self._get_recent_history(limit=10)
            post_content: PostContent = self.writer.create_post(trend_summary, recent_posts=recent_posts)

            # ── 3. Media (optional) ─────────────────────────────────────────────────
            logger.info("\n[STEP 3/4] 🖼️  Media upload")
            media_ids = None
            has_image = getattr(post_content, 'has_image', True)
            
            if has_image and settings.MEDIA_DIR.exists():
                # 1-ci cəhd: Dinamik şəkil hazırlayıb yükləmək
                trend_title = post_content.chosen_trend
                hook_text = post_content.tweets[0] if post_content.tweets else ""
                image_prompt = getattr(post_content, 'image_prompt', None)
                media_id = self.media_handler.generate_and_upload(trend_title, hook_text, image_prompt=image_prompt)
                
                # 2-ci cəhd (fallback): Hər hansı xəta halında təsadüfi statik şəkil seçmək
                if not media_id:
                    logger.info("⚠️  Dinamik şəkil yaradılması alınmadı, təsadüfi statik şəkil seçilir...")
                    media_id = self.media_handler.get_and_upload_random()
                
                if media_id:
                    media_ids = [media_id]
            else:
                logger.info("ℹ️  DeepSeek bu post üçün şəkil istifadəsini məqsədəuyğun saymadı. Şəkilsiz post göndərilir.")

            # ── 4. X: Post/Thread publishing ──────────────────────────────────────
            logger.info(f"\n[STEP 4/4] 🐦 X — {'Thread' if post_content.is_thread else 'Post'} publishing")

            if post_content.is_thread:
                result = self.twitter.post_thread(
                    tweets=post_content.tweets,
                    first_media_ids=media_ids,
                )
                tweet_ids = result.get("thread_ids", [])
                success = result["success"]
                error = result.get("error")
            else:
                result = self.twitter.post_tweet(
                    text=post_content.tweets[0],
                    media_ids=media_ids,
                )
                tweet_ids = [result["tweet_id"]] if result.get("tweet_id") else []
                success = result["success"]
                error = result.get("error")

            # ── Nəticəni saxla ────────────────────────────────────────────────
            self._save_history(
                run_time=run_time,
                post_content=post_content,
                tweet_ids=tweet_ids,
                success=success,
                error=error,
            )

            if success:
                logger.info("\n" + "=" * 60)
                logger.info("✅ PIPELINE COMPLETED SUCCESSFULLY")
                logger.info(f"   Chosen trend: {post_content.chosen_trend}")
                logger.info(f"   Post type: {post_content.post_type.upper()}")
                logger.info(f"   Tweet count: {post_content.tweet_count}")
                if tweet_ids and not settings.DRY_RUN:
                    logger.info(f"   URL: https://x.com/i/web/status/{tweet_ids[0]}")
                logger.info("=" * 60)

            return {
                "success": success,
                "post_type": post_content.post_type,
                "chosen_trend": post_content.chosen_trend,
                "tweet_ids": tweet_ids,
                "error": error,
            }

        except Exception as e:
            logger.error(f"\n❌ KRİTİK XƏTA: {e}", exc_info=True)
            self._save_history(
                run_time=run_time,
                post_content=None,
                tweet_ids=[],
                success=False,
                error=str(e),
            )
            return {
                "success": False,
                "post_type": None,
                "chosen_trend": None,
                "tweet_ids": [],
                "error": str(e),
            }

    # ─────────────────────────────────────────────────────────────────────────
    # Tarix saxlama
    # ─────────────────────────────────────────────────────────────────────────

    def _save_history(
        self,
        run_time: str,
        post_content: PostContent | None,
        tweet_ids: list[str],
        success: bool,
        error: str | None,
        quoted_tweet_id: str | None = None,
    ) -> None:
        """Göndərilmiş postu history.json-a əlavə edir."""
        record = {
            "run_time": run_time,
            "success": success,
            "post_type": post_content.post_type if post_content else None,
            "chosen_trend": post_content.chosen_trend if post_content else None,
            "reasoning": post_content.reasoning if post_content else None,
            "stance_summary": post_content.stance_summary if post_content else None,
            "tweets": post_content.tweets if post_content else [],
            "tweet_ids": tweet_ids,
            "quoted_tweet_id": quoted_tweet_id,
            "dry_run": settings.DRY_RUN,
            "error": error,
        }

        history: list[dict] = []
        if settings.HISTORY_FILE.exists():
            try:
                with open(settings.HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.append(record)

        with open(settings.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        logger.debug(f"📁 Tarix saxlandı — {settings.HISTORY_FILE}")

    def _get_recent_history(self, limit: int = 10) -> list[dict]:
        """Oxşar mövzulardan qaçmaq və ardıcıllığı qorumaq üçün son uğurlu postları qaytarır."""
        if not settings.HISTORY_FILE.exists():
            return []
        try:
            with open(settings.HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            # Yalnız uğurlu postları süzgəcdən keçir
            successful_posts = [
                h for h in history
                if h.get("success") and h.get("tweets")
            ]
            return successful_posts[-limit:]
        except Exception as e:
            logger.warning(f"⚠️  Tarixçəni oxumaq mümkün olmadı: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Video Repost Axarı
    # ─────────────────────────────────────────────────────────────────────────

    def run_video_repost(self) -> dict:
        """
        Gündəlik video repost axarını idarə edir:
        1. Niche üzrə X-də son konfiqurasiya edilən saatda paylaşılan video tweetləri axtarır.
        2. Rəsmi/ciddi hesabları (followeri çox olan) süzgəcdən keçirir və engagement-ə görə sıralayır.
        3. Tapılan ən populyar videoları DeepSeek vasitəsilə yoxlayaraq ciddi biznes videosu olmasını təsdiqləyir.
        4. Seçilmiş videonun linkini şərhə əlavə edərək quote edir və paylaşır.
        """
        run_time = datetime.now(timezone.utc).isoformat()
        logger.info("=" * 60)
        logger.info(f"🚀 Video Repost pipeline starting — {run_time}")
        logger.info("=" * 60)

        try:
            # ── 1. Video Axtarışı ──────────────────────────────────────
            window_hours = getattr(settings, "VIDEO_REPOST_WINDOW_HOURS", 24)
            logger.info(f"\n[STEP 1/3] 🔍 Searching for recent video tweets in niche (last {window_hours} hours)...")
            
            # Konfiqurasiya edilən saatlıq zaman zolağı (X API ISO 8601 UTC formatında start_time tələb edir)
            start_time_dt = datetime.now(timezone.utc) - timedelta(hours=window_hours)
            start_time = start_time_dt.isoformat().replace("+00:00", "Z")
            
            # Explore kateqoriyalarını (tech, business, finance, crypto) hədəfləyən qlobal açar sözlər
            query = (
                'has:videos ("technology" OR "business" OR "finance" OR "cryptocurrency" '
                'OR "crypto" OR "bitcoin" OR "ethereum" OR "tech" OR "market" '
                'OR "economy" OR "economics" OR "tax" OR "spending" OR "inflation" '
                'OR "money" OR "stocks" OR "investing") '
                'min_replies:15 -is:reply -is:retweet'
            )
            
            tweets = self.twitter.search_video_tweets(query, start_time=start_time, max_results=30)
            if not tweets:
                logger.warning(f"⚠️ No video tweets found in this niche in the last {window_hours} hours.")
                return {"success": False, "error": f"No video tweets found in the last {window_hours} hours"}

            # ── 2. Seçim və Süzgəc (Ciddi Kanallar & Populyarlıq) ──────────────────────
            logger.info("\n[STEP 2/3] 📊 Filtering and selecting authoritative videos...")
            already_reposted = self._get_already_reposted_tweet_ids()
            
            valid_tweets = []
            min_followers = getattr(settings, "VIDEO_REPOST_MIN_FOLLOWERS", 50000)
            
            for tweet in tweets:
                tweet_id_str = str(tweet["id"])
                if tweet_id_str in already_reposted:
                    logger.debug(f"   Skipping already attempted tweet ID: {tweet_id_str}")
                    continue
                
                # Ciddi hesab və ya viral post yoxlaması
                followers = tweet.get("followers_count", 0)
                is_verified = tweet.get("verified", False)
                
                metrics = tweet.get("public_metrics") or {}
                views = metrics.get("impression_count", 0)
                likes = metrics.get("like_count", 0)
                retweets = metrics.get("retweet_count", 0)
                
                # Əgər hesab balacadırsa və verified deyilsə, lakin post özü viral olubsa (baxış >= 10k, like >= 50, retweets >= 10), icazə veririk
                is_viral = views >= 10000 or likes >= 50 or retweets >= 10
                
                if followers < min_followers and not is_verified and not is_viral:
                    logger.debug(f"   Skipping account @{tweet['username']} with {followers} followers (not verified, no viral engagement, min {min_followers} required)")
                    continue
                
                valid_tweets.append((tweet, views))
            
            if not valid_tweets:
                logger.warning("⚠️ No new video tweets found from authoritative accounts.")
                return {"success": False, "error": "No new authoritative video tweets available"}
                
            # Ən yüksək baxış sayına (views/impressions) görə sırala (beləcə ən çox baxış yığan öndə olur)
            valid_tweets.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"   Son {window_hours} saatlıq video namizədlər (Baxış sayına görə sıralanmış):")
            for idx, (tweet, score) in enumerate(valid_tweets[:20]):
                logger.info(f"      [{idx}] ID: {tweet['id']} by @{tweet['username']} | Views: {score} | Likes: {tweet['public_metrics'].get('like_count', 0)}")

            # İlk 20 ən çox izlənən namizədi götürürük
            candidates = [x[0] for x in valid_tweets[:20]]
            
            # ── 3. Mövzu Ciddiliyinin Analizi (DeepSeek) ───────────────────────────
            logger.info("\n[STEP 3/3] 🧠 DeepSeek — Verifying business relevance...")
            chosen_index = self.writer.verify_video_relevance(candidates)
            
            if chosen_index is None or chosen_index < 0 or chosen_index >= len(candidates):
                logger.warning("⚠️ DeepSeek rejected all video candidates as unrelated or non-professional.")
                return {"success": False, "error": "No relevant professional videos found"}
                
            chosen_tweet = candidates[chosen_index]
            chosen_id_str = str(chosen_tweet["id"])
            
            # Seçilmiş tweet-in baxış sayını tapırıq
            chosen_score = 0
            for t, sc in valid_tweets:
                if t["id"] == chosen_id_str:
                    chosen_score = sc
                    break
            
            logger.info(f"\n   ✅ Selected Tweet ID: {chosen_id_str} by @{chosen_tweet['username']}")
            logger.info(f"   Engagement Score: {chosen_score} (Likes: {chosen_tweet['public_metrics'].get('like_count', 0)}, Retweets: {chosen_tweet['public_metrics'].get('retweet_count', 0)})")
            logger.info(f"   Original Text: {chosen_tweet['text'][:120]}...")

            # ── 4. Şərh Yazılması və Paylaşma ────────────────────────────────────
            logger.info("   🧠 DeepSeek — Generating comment...")
            comment = self.writer.create_video_comment(chosen_tweet["text"])

            # Native Video Quote: Appending /video/1 forces X to render the video natively on the timeline.
            tweet_url = f"https://x.com/{chosen_tweet['username']}/status/{chosen_id_str}/video/1"
            full_text = f"{comment} {tweet_url}"

            logger.info(f"   🐦 Reposting to X as native video...")
            result = self.twitter.post_tweet(
                text=full_text
            )
            
            success = result["success"]
            error = result.get("error")
            tweet_ids = [result["tweet_id"]] if result.get("tweet_id") else []

            if success:
                # Uğurlu paylaşımı tarixçəyə yaz
                post_content = PostContent(
                    post_type="video_repost",
                    tweets=[comment],
                    chosen_trend=f"Video Repost: {chosen_id_str}",
                    reasoning=f"Selected by DeepSeek from candidates (Score: {chosen_score})",
                    image_prompt="",
                    has_image=False,
                    stance_summary=f"Commented on video: {comment[:80]}..."
                )
                
                self._save_history(
                    run_time=run_time,
                    post_content=post_content,
                    tweet_ids=tweet_ids,
                    success=True,
                    error=None,
                    quoted_tweet_id=chosen_id_str
                )

                logger.info("\n" + "=" * 60)
                logger.info("✅ VIDEO REPOST COMPLETED SUCCESSFULLY")
                logger.info(f"   Quoted Tweet: https://x.com/i/web/status/{chosen_id_str}")
                if tweet_ids and not settings.DRY_RUN:
                    logger.info(f"   Your Tweet: https://x.com/i/web/status/{tweet_ids[0]}")
                logger.info("=" * 60)

                return {
                    "success": True,
                    "post_type": "video_repost",
                    "quoted_tweet_id": chosen_id_str,
                    "tweet_ids": tweet_ids,
                    "error": None,
                }
            else:
                logger.error(f"❌ Failed to quote tweet ID {chosen_id_str}: {error}")
                
                # Bu ID-ni uğursuz cəhd kimi tarixçəyə yazırıq ki, gələcəkdə təkrar yoxlamayaq
                post_content = PostContent(
                    post_type="video_repost",
                    tweets=[comment],
                    chosen_trend=f"Video Repost (Failed): {chosen_id_str}",
                    reasoning=f"Failed to quote-tweet: {error}",
                    image_prompt="",
                    has_image=False,
                    stance_summary=f"Commented on video: {comment[:80]}..."
                )
                self._save_history(
                    run_time=run_time,
                    post_content=post_content,
                    tweet_ids=[],
                    success=False,
                    error=error,
                    quoted_tweet_id=chosen_id_str
                )
                
                return {
                    "success": False,
                    "post_type": "video_repost",
                    "quoted_tweet_id": None,
                    "tweet_ids": [],
                    "error": error,
                }

        except Exception as e:
            logger.error(f"\n❌ KRİTİK XƏTA (Video Repost): {e}", exc_info=True)
            self._save_history(
                run_time=run_time,
                post_content=None,
                tweet_ids=[],
                success=False,
                error=str(e)
            )
            return {
                "success": False,
                "post_type": "video_repost",
                "quoted_tweet_id": None,
                "tweet_ids": [],
                "error": str(e)
            }

    def _get_already_reposted_tweet_ids(self) -> set[str]:
        """Tarixçədən əvvəllər quote edilmiş video tweet ID-lərini qaytarır."""
        reposted_ids = set()
        if not settings.HISTORY_FILE.exists():
            return reposted_ids
        try:
            with open(settings.HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            for record in history:
                if record.get("post_type") == "video_repost":
                    quoted_id = record.get("quoted_tweet_id")
                    if quoted_id:
                        reposted_ids.add(str(quoted_id))
        except Exception as e:
            logger.warning(f"⚠️  Tarixçəni oxumaq mümkün olmadı: {e}")
        return reposted_ids
