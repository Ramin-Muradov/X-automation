"""
X Automation — Gemini AI Mətn Generatoru
Mövcud mövzular əsasında Twitter/X postu üçün mətn yaradır.
"""

import json
import random
from pathlib import Path
from typing import Optional

import google.generativeai as genai

from config.settings import settings
from src.logger import setup_logger

logger = setup_logger(__name__, settings.LOGS_DIR / "automation.log", settings.LOG_LEVEL)


class AIGenerator:
    """Gemini AI istifadə edərək post mətnləri yaradır."""

    # Post üçün standart sistem promptu
    SYSTEM_PROMPT = """Sən X (Twitter) platforması üçün cəlbedici, qısa və dəyərli postlar yazan bir ekspertsən.

Qaydalar:
- Post maksimum 280 simvol olmalıdır
- Cəlbedici, maraqlı və oxunaqlı olmalıdır
- Hashtag-lar əlavə et (2-4 ədəd)
- Emoji istifadə et (1-3 ədəd)
- Suallar, faktlar və ya dəyərli məlumatlar ver
- Reklam xarakteri daşımamalıdır
- Yalnız post mətnini ver, izahat yox
"""

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=self.SYSTEM_PROMPT,
        )
        self.topics = self._load_topics()
        logger.info("✅ Gemini AI generatoru hazırdır.")

    def _load_topics(self) -> list[dict]:
        """topics.json faylından mövzuları oxuyur."""
        if not settings.TOPICS_FILE.exists():
            logger.warning(
                f"⚠️  {settings.TOPICS_FILE} tapılmadı. Standart mövzular istifadə edilir."
            )
            return self._default_topics()

        with open(settings.TOPICS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            topics = data.get("topics", [])
            logger.info(f"📋 {len(topics)} mövzu yükləndi.")
            return topics

    def _default_topics(self) -> list[dict]:
        """topics.json olmadıqda istifadə olunan standart mövzular."""
        return [
            {"category": "Texnologiya", "prompt": "Süni zəka sahəsindəki son inkişaflar haqqında bir post yaz"},
            {"category": "Motivasiya", "prompt": "Uğur və əzm haqqında ilhamverici bir post yaz"},
            {"category": "Elm", "prompt": "Maraqlı elmi bir fakt haqqında post yaz"},
            {"category": "Produktivlik", "prompt": "Gündəlik həyatı asanlaşdıran bir məsləhət ver"},
        ]

    def generate_post(
        self,
        topic: Optional[dict] = None,
        extra_instruction: str = "",
    ) -> str:
        """
        Verilmiş mövzu əsasında post mətni yaradır.

        Args:
            topic:             Mövzu dict-i (category, prompt açarları olmalı)
            extra_instruction: Əlavə yönlendirmə (istəyə bağlı)

        Returns:
            Hazır post mətni (≤280 simvol)
        """
        if topic is None:
            topic = random.choice(self.topics)

        language_note = f"Post {settings.POST_LANGUAGE} dilində olsun." if settings.POST_LANGUAGE else ""
        full_prompt = f"{topic['prompt']}. {language_note} {extra_instruction}".strip()

        logger.info(f"🤖 AI mətni yaradılır — Mövzu: [{topic.get('category', 'Ümumi')}]")

        response = self.model.generate_content(full_prompt)
        text = response.text.strip()

        # 280 simvol həddini aşırsa kəs
        if len(text) > 280:
            text = text[:277] + "..."
            logger.warning(f"⚠️  Mətn 280 simvolu keçdi, kəsildi.")

        logger.info(f"✍️  Yaradılan mətn ({len(text)} simvol): {text[:60]}...")
        return text

    def generate_with_retry(self, max_retries: int = 3) -> str:
        """
        Xəta halında yenidən cəhd edərək post yaradır.

        Args:
            max_retries: Maksimum cəhd sayı

        Returns:
            Hazır post mətni
        """
        for attempt in range(1, max_retries + 1):
            try:
                topic = random.choice(self.topics)
                return self.generate_post(topic)
            except Exception as e:
                logger.warning(f"⚠️  Cəhd {attempt}/{max_retries} uğursuz: {e}")
                if attempt == max_retries:
                    raise RuntimeError(
                        f"❌ AI generasiyası {max_retries} cəhddən sonra da uğursuz oldu."
                    ) from e
