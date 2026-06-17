"""
X Automation — Scheduler
APScheduler ilə gündə bir dəfə müəyyən saatda
PostManager.run() metodunu işə salır.
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config.settings import settings
from src.post_manager import PostManager
from src.logger import setup_logger

logger = setup_logger(__name__, settings.LOGS_DIR / "automation.log", settings.LOG_LEVEL)


def _run_job():
    """Scheduler tərəfindən çağrılan əsas funksiya."""
    manager = PostManager()
    manager.run()


def _run_video_repost_job():
    """Scheduler tərəfindən çağrılan video repost funksiyası."""
    manager = PostManager()
    manager.run_video_repost()


def start_scheduler():
    """
    APScheduler-i konfiqurasiya edib işə salır.
    Konfiqurasiya olunan POST_TIME və VIDEO_REPOST_TIME vaxtlarında işləyir.
    """
    times = [t.strip() for t in settings.POST_TIME.split(",") if t.strip()]
    if not times:
        logger.error("❌ POST_TIME boşdur.")
        raise ValueError("POST_TIME cannot be empty")

    tz = pytz.timezone(settings.TIMEZONE)
    scheduler = BlockingScheduler(timezone=tz)

    logger.info("⏰ Scheduler konfiqurasiyası:")
    logger.info(f"   Saha: {settings.BUSINESS_NICHE}")
    logger.info(f"   Zaman zolağı: {settings.TIMEZONE}")
    logger.info(f"   Test rejimi: {'✅ AKTİV (real post göndərilməyəcək)' if settings.DRY_RUN else '❌ DEAKTİV (real post göndəriləcək)'}")
    logger.info("   Planlaşdırılan vaxtlar:")

    for idx, t_str in enumerate(times):
        try:
            hour, minute = map(int, t_str.split(":"))
        except ValueError:
            logger.error(f"   ❌ Yanlış POST_TIME formatı: '{t_str}'. HH:MM olmalıdır.")
            raise

        job_id = f"daily_post_{idx}"
        job = scheduler.add_job(
            func=_run_job,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
            id=job_id,
            name=f"X Post — hər gün {t_str} ({settings.TIMEZONE})",
            replace_existing=True,
            misfire_grace_time=300,   # 5 dəqiqəyə qədər gecikməyə icazə
        )
        from datetime import datetime
        next_run = getattr(job, 'next_run_time', None) or job.trigger.get_next_fire_time(None, datetime.now(tz))
        logger.info(f"      - Normal Post: {t_str} (Növbəti: {next_run})")

    # ── Video Repost Planlaması ─────────────────────────────────────────────
    if settings.VIDEO_REPOST_ENABLED:
        vr_time = settings.VIDEO_REPOST_TIME.strip()
        try:
            hour, minute = map(int, vr_time.split(":"))
            job_id = "video_repost_job"
            job = scheduler.add_job(
                func=_run_video_repost_job,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
                id=job_id,
                name=f"X Video Repost — hər gün {vr_time} ({settings.TIMEZONE})",
                replace_existing=True,
                misfire_grace_time=300,
            )
            from datetime import datetime
            next_run = getattr(job, 'next_run_time', None) or job.trigger.get_next_fire_time(None, datetime.now(tz))
            logger.info(f"      - Video Repost: {vr_time} (Növbəti: {next_run})")
        except ValueError:
            logger.error(f"   ❌ Yanlış VIDEO_REPOST_TIME formatı: '{vr_time}'. HH:MM olmalıdır.")
            raise

    logger.info("")
    logger.info("▶️  Scheduler işə düşdü. Dayandırmaq üçün Ctrl+C basın.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("⏹️  Scheduler dayandırıldı.")
