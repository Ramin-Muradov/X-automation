"""
X Automation — Media Handler
Şəkil fayllarını X API-yə yükləmək üçün emal edir.
"""

import random
from pathlib import Path
from typing import Optional

import tweepy
from PIL import Image

from config.settings import settings
from src.image_generator import DynamicImageGenerator
from src.logger import setup_logger

logger = setup_logger(__name__, settings.LOGS_DIR / "automation.log", settings.LOG_LEVEL)

# X API-nin qəbul etdiyi şəkil formatları
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
# X API üçün maksimum şəkil ölçüsü (5 MB)
MAX_IMAGE_SIZE_MB = 5
MAX_IMAGE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024


class MediaHandler:
    """Şəkil seçimi, emalı və X API-yə yüklənməsini idarə edir."""

    def __init__(self, api_v1: tweepy.API):
        """
        Args:
            api_v1: tweepy v1.1 API nümunəsi (media upload üçün tələb olunur)
        """
        self.api_v1 = api_v1
        self.media_dir = settings.MEDIA_DIR
        self.generator = DynamicImageGenerator()

    def get_random_image(self) -> Optional[Path]:
        """
        Media qovluğundan təsadüfi bir şəkil seçir.

        Returns:
            Şəkil faylının yolu və ya None (qovluq boşdursa)
        """
        if not self.media_dir.exists():
            logger.warning(f"⚠️  Media qovluğu tapılmadı: {self.media_dir}")
            return None

        images = [
            f for f in self.media_dir.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        if not images:
            logger.info("ℹ️  Media qovluğunda şəkil yoxdur. Şəkilsiz post göndəriləcək.")
            return None

        chosen = random.choice(images)
        logger.info(f"🖼️  Seçilmiş şəkil: {chosen.name}")
        return chosen

    def optimize_image(self, image_path: Path) -> Path:
        """
        Şəkili X API üçün optimallaşdırır (həddən böyük olduqda kiçildir).

        Args:
            image_path: Orijinal şəkil yolu

        Returns:
            Optimallaşdırılmış şəkil yolu
        """
        if image_path.stat().st_size <= MAX_IMAGE_BYTES:
            return image_path  # Ölçü uyğundur, dəyişmə lazım deyil

        logger.info(f"🔧 Şəkil optimallaşdırılır: {image_path.name}")

        with Image.open(image_path) as img:
            # RGB-yə çevir (RGBA/palette rejimləri üçün)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Optimallaşdırılmış versiyonu müvəqqəti yolda saxla
            optimized_path = image_path.parent / f"_optimized_{image_path.name}"
            quality = 85
            while quality >= 50:
                img.save(optimized_path, "JPEG", quality=quality, optimize=True)
                if optimized_path.stat().st_size <= MAX_IMAGE_BYTES:
                    logger.info(f"✅ Optimallaşdırıldı (keyfiyyət={quality}): {optimized_path.stat().st_size / 1024:.1f} KB")
                    return optimized_path
                quality -= 10

        logger.warning("⚠️  Şəkil optimallaşdırılamadı, orijinal istifadə edilir.")
        return image_path

    def upload_image(self, image_path: Path) -> Optional[str]:
        """
        Şəkili X API-yə yükləyir və media_id qaytarır.

        Args:
            image_path: Yüklənəcək şəkil yolu

        Returns:
            media_id string və ya None (xəta halında)
        """
        try:
            optimized = self.optimize_image(image_path)
            logger.info(f"⬆️  Şəkil yüklənir: {image_path.name}")

            media = self.api_v1.media_upload(filename=str(optimized))
            media_id = str(media.media_id)
            logger.info(f"✅ Şəkil yükləndi — media_id: {media_id}")

            # Müvəqqəti optimallaşdırılmış faylı sil
            if optimized != image_path and optimized.exists():
                optimized.unlink()

            return media_id

        except Exception as e:
            logger.error(f"❌ Şəkil yükləmə xətası: {e}")
            return None

    def get_and_upload_random(self) -> Optional[str]:
        """
        Təsadüfi şəkil seçib yükləyir.

        Returns:
            media_id string və ya None
        """
        image_path = self.get_random_image()
        if image_path is None:
            return None
        return self.upload_image(image_path)

    def generate_dynamic_image(self, trend_title: str, body_text: str, image_prompt: Optional[str] = None) -> Optional[Path]:
        """
        Trend mövzusu və post mətni əsasında dinamik şəkil hazırlayır.

        Args:
            trend_title: Trend başlığı
            body_text: Postun əsas mətni / hook hissəsi
            image_prompt: AI şəkil promptu (varsa)

        Returns:
            Şəkil faylının yolu və ya None (xəta halında)
        """
        try:
            output_path = self.media_dir / "dynamic_post.png"
            logger.info(f"🎨 Şəkil generatoru çağırılır. Trend: '{trend_title}'")
            
            # Save a dynamic image card
            self.generator.generate(
                trend_title=trend_title,
                body_text=body_text,
                output_path=output_path,
                image_prompt=image_prompt
            )
            
            if output_path.exists():
                logger.info(f"✅ Dinamik şəkil yaradıldı: {output_path.name}")
                return output_path
            return None
        except Exception as e:
            logger.error(f"❌ Dinamik şəkil yaradılarkən xəta: {e}", exc_info=True)
            return None

    def generate_and_upload(self, trend_title: str, body_text: str, image_prompt: Optional[str] = None) -> Optional[str]:
        """
        Dinamik şəkil hazırlayır, X-ə yükləyir və müvəqqəti faylı silir.

        Args:
            trend_title: Trend başlığı
            body_text: Postun əsas mətni / hook hissəsi
            image_prompt: AI şəkil promptu (varsa)

        Returns:
            media_id string və ya None
        """
        image_path = self.generate_dynamic_image(trend_title, body_text, image_prompt=image_prompt)
        if not image_path:
            return None

        try:
            media_id = self.upload_image(image_path)
            return media_id
        finally:
            # Müvəqqəti dinamik şəkli mütləq sil
            if image_path.exists() and image_path.name == "dynamic_post.png":
                try:
                    image_path.unlink()
                    logger.debug(f"🗑️ Müvəqqəti dinamik şəkil silindi: {image_path.name}")
                except Exception as e:
                    logger.warning(f"⚠️ Müvəqqəti dinamik şəkli silmək mümkün olmadı: {e}")
