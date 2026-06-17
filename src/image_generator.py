"""
X Automation — Dynamic Image Generator
Generates beautiful social media cards using Pillow.
Supports 4 premium templates: Neon Cyberpunk, Sunset Glow, Editorial Light, and Corporate Grid.
"""

import random
import re
from pathlib import Path
from typing import Optional, List, Tuple
import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config.settings import settings
from src.logger import setup_logger

logger = setup_logger(__name__, settings.LOGS_DIR / "automation.log", settings.LOG_LEVEL)

class DynamicImageGenerator:
    """Generates custom visual images for trends and tweets with multiple design styles."""

    # Standard Twitter/X image dimensions (16:9 ratio)
    WIDTH = 1200
    HEIGHT = 675

    # System fonts
    FONT_SANS = "/System/Library/Fonts/HelveticaNeue.ttc"
    FONT_SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"
    FONT_SERIF_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"

    def __init__(self):
        # Fallback to default font if needed
        self.use_fallback = False
        if not Path(self.FONT_SANS).exists():
            self.use_fallback = True

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> List[str]:
        """Wraps text to fit within a maximum pixel width."""
        lines = []
        for paragraph in text.split("\n"):
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            current_line = []
            for word in words:
                current_line.append(word)
                line_str = " ".join(current_line)
                bbox = draw.textbbox((0, 0), line_str, font=font)
                w = bbox[2] - bbox[0]
                if w > max_width:
                    if len(current_line) == 1:
                        # Force single long word
                        lines.append(line_str)
                        current_line = []
                    else:
                        current_line.pop()
                        lines.append(" ".join(current_line))
                        current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))
        return lines

    def _get_best_font_size(
        self,
        draw: ImageDraw.Draw,
        text: str,
        font_path: str,
        max_width: int,
        max_height: int,
        start_size: int = 40,
        min_size: int = 18,
        bold: bool = False,
        index: int = 0
    ) -> Tuple[ImageFont.FreeTypeFont, List[str], int]:
        """Dynamically scales font size down until text fits max bounds."""
        size = start_size
        while size >= min_size:
            try:
                if font_path.endswith(".ttc"):
                    font = ImageFont.truetype(font_path, size, index=index)
                else:
                    font = ImageFont.truetype(font_path, size)
            except Exception:
                font = ImageFont.load_default()
                lines = self._wrap_text(text, font, max_width, draw)
                return font, lines, 12

            lines = self._wrap_text(text, font, max_width, draw)
            total_height = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line or "A", font=font)
                h = bbox[3] - bbox[1]
                total_height += h + 10  # spacing
            
            if total_height <= max_height:
                return font, lines, size
            size -= 2

        try:
            if font_path.endswith(".ttc"):
                font = ImageFont.truetype(font_path, min_size, index=index)
            else:
                font = ImageFont.truetype(font_path, min_size)
        except Exception:
            font = ImageFont.load_default()
        lines = self._wrap_text(text, font, max_width, draw)
        return font, lines, min_size

    def _create_gradient(self, color1: Tuple[int, int, int], color2: Tuple[int, int, int], direction: str = "diagonal") -> Image.Image:
        """Creates a smooth bilinear scaled gradient image."""
        if direction == "horizontal":
            w, h = 10, 1
        elif direction == "vertical":
            w, h = 1, 10
        else: # diagonal
            w, h = 10, 10

        tiny_img = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(tiny_img)
        r1, g1, b1 = color1
        r2, g2, b2 = color2

        if direction == "horizontal":
            for x in range(w):
                t = x / (w - 1)
                r = int(r1 + (r2 - r1) * t)
                g = int(g1 + (g2 - g1) * t)
                b = int(b1 + (b2 - b1) * t)
                draw.line([(x, 0), (x, h - 1)], fill=(r, g, b))
        elif direction == "vertical":
            for y in range(h):
                t = y / (h - 1)
                r = int(r1 + (r2 - r1) * t)
                g = int(g1 + (g2 - g1) * t)
                b = int(b1 + (b2 - b1) * t)
                draw.line([(0, y), (w - 1, y)], fill=(r, g, b))
        else: # diagonal
            for x in range(w):
                for y in range(h):
                    t = (x + y) / (w + h - 2)
                    r = int(r1 + (r2 - r1) * t)
                    g = int(g1 + (g2 - g1) * t)
                    b = int(b1 + (b2 - b1) * t)
                    draw.point((x, y), fill=(r, g, b))

        return tiny_img.resize((self.WIDTH, self.HEIGHT), Image.Resampling.BILINEAR)

    # ─────────────────────────────────────────────────────────────────────────
    # TEMPLATE 1: Neon Cyberpunk (Dark, Cyan-to-Purple accent)
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_neon_cyberpunk(self, trend_title: str, text: str) -> Image.Image:
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), (10, 14, 26))  # Very dark indigo-blue
        draw = ImageDraw.Draw(img)

        # Draw subtle cyber grid lines
        grid_color = (25, 33, 58)
        for x in range(0, self.WIDTH, 80):
            draw.line([(x, 0), (x, self.HEIGHT)], fill=grid_color, width=1)
        for y in range(0, self.HEIGHT, 80):
            draw.line([(0, y), (self.WIDTH, y)], fill=grid_color, width=1)

        # Draw left accent neon bar (cyan/indigo gradient)
        accent_color = (6, 182, 212) # cyan
        for i in range(12): # neon glow width
            opacity_color = (accent_color[0], accent_color[1], accent_color[2])
            draw.line([(40 + i, 60), (40 + i, self.HEIGHT - 60)], fill=opacity_color, width=1)

        # Fonts
        title_font = ImageFont.truetype(self.FONT_SANS, 56, index=1) # Bold
        sub_font = ImageFont.truetype(self.FONT_SANS, 22, index=10) # Medium
        
        # Trend badge
        draw.text((80, 70), "🔥 TRENDING INSIGHT", font=sub_font, fill=(6, 182, 212))

        # Title (Trend Title)
        title_wrapped = self._wrap_text(trend_title, title_font, self.WIDTH - 200, draw)
        y_cursor = 110
        for line in title_wrapped[:2]: # limit to 2 lines
            draw.text((80, y_cursor), line, font=title_font, fill=(255, 255, 255))
            y_cursor += 65

        # Content card container
        card_x0, card_y0 = 80, y_cursor + 20
        card_x1, card_y1 = self.WIDTH - 80, self.HEIGHT - 90
        draw.rectangle([(card_x0, card_y0), (card_x1, card_y1)], fill=(18, 24, 43), outline=(99, 102, 241), width=2)

        # Card text (dynamic sizing)
        card_draw = ImageDraw.Draw(img)
        body_font, body_wrapped, _ = self._get_best_font_size(
            draw=card_draw,
            text=text,
            font_path=self.FONT_SANS,
            max_width=(card_x1 - card_x0) - 60,
            max_height=(card_y1 - card_y0) - 60,
            start_size=32,
            min_size=20,
            index=0 # Regular
        )

        card_y = card_y0 + 35
        for line in body_wrapped:
            card_draw.text((card_x0 + 30, card_y), line, font=body_font, fill=(226, 232, 240))
            card_y += body_font.size + 10

        # Footer watermark
        draw.text((self.WIDTH - 200, self.HEIGHT - 50), "X Automation 🤖", font=sub_font, fill=(71, 85, 105))
        return img

    # ─────────────────────────────────────────────────────────────────────────
    # TEMPLATE 2: Sunset Glow (Glassmorphic Card over Purple/Orange Gradient)
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_sunset_glow(self, trend_title: str, text: str) -> Image.Image:
        # Create Sunset Gradient Background
        color1 = (30, 27, 75)   # Deep indigo
        color2 = (180, 83, 9)   # Sunset orange/amber
        img = self._create_gradient(color1, color2, direction="diagonal")
        draw = ImageDraw.Draw(img)

        # Draw a glowing decorative blurred circle/ellipse in the background
        # Create alpha layer for drawing shapes
        overlay = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
        ol_draw = ImageDraw.Draw(overlay)
        
        # Transparent card in the center (glassmorphism)
        card_x0, card_y0 = 100, 100
        card_x1, card_y1 = self.WIDTH - 100, self.HEIGHT - 100
        ol_draw.rounded_rectangle(
            [(card_x0, card_y0), (card_x1, card_y1)],
            radius=20,
            fill=(15, 23, 42, 205), # Dark slate, semi-transparent
            outline=(255, 255, 255, 60),
            width=2
        )
        
        # Composite glass card onto gradient
        img.paste(overlay, (0, 0), overlay)

        # Draw texts
        draw = ImageDraw.Draw(img)
        badge_font = ImageFont.truetype(self.FONT_SANS, 20, index=10) # Medium
        title_font = ImageFont.truetype(self.FONT_SANS, 48, index=1)  # Bold

        # Header Badge
        draw.text((card_x0 + 40, card_y0 + 35), "📊 MARKET BREAKOUT", font=badge_font, fill=(251, 191, 36)) # Yellow badge

        # Trend Title
        title_wrapped = self._wrap_text(trend_title, title_font, (card_x1 - card_x0) - 80, draw)
        y_cursor = card_y0 + 75
        for line in title_wrapped[:2]:
            draw.text((card_x0 + 40, y_cursor), line, font=title_font, fill=(255, 255, 255))
            y_cursor += 55

        # Body Text
        body_font, body_wrapped, _ = self._get_best_font_size(
            draw=draw,
            text=text,
            font_path=self.FONT_SANS,
            max_width=(card_x1 - card_x0) - 80,
            max_height=(card_y1 - y_cursor) - 70,
            start_size=30,
            min_size=18,
            index=7 # Light
        )

        card_y = y_cursor + 25
        for line in body_wrapped:
            draw.text((card_x0 + 40, card_y), line, font=body_font, fill=(241, 245, 249))
            card_y += body_font.size + 10

        return img

    # ─────────────────────────────────────────────────────────────────────────
    # TEMPLATE 3: Editorial Light (Sophisticated Cream & Georgia Serif)
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_editorial_light(self, trend_title: str, text: str) -> Image.Image:
        # Solid warm off-white background
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), (244, 243, 238)) # cream
        draw = ImageDraw.Draw(img)

        # Thin double borders
        draw.rectangle([(30, 30), (self.WIDTH - 30, self.HEIGHT - 30)], outline=(41, 37, 36), width=1) # dark charcoal border
        draw.rectangle([(35, 35), (self.WIDTH - 35, self.HEIGHT - 35)], outline=(41, 37, 36), width=2)

        # Fonts
        badge_font = ImageFont.truetype(self.FONT_SANS, 18, index=10) # Sans Medium
        title_font = ImageFont.truetype(self.FONT_SERIF_BOLD, 52)
        body_font = ImageFont.truetype(self.FONT_SERIF, 28)

        # Category/Badge
        draw.text((80, 75), "FINANCIAL DISPATCH", font=badge_font, fill=(153, 27, 27)) # Deep red accent

        # Trend Title
        title_wrapped = self._wrap_text(trend_title, title_font, self.WIDTH - 160, draw)
        y_cursor = 115
        for line in title_wrapped[:2]:
            draw.text((80, y_cursor), line, font=title_font, fill=(28, 25, 23))
            y_cursor += 62

        # A beautiful separating line
        draw.line([(80, y_cursor + 15), (self.WIDTH - 80, y_cursor + 15)], fill=(120, 113, 108), width=1)

        # Body Text
        body_font, body_wrapped, _ = self._get_best_font_size(
            draw=draw,
            text=text,
            font_path=self.FONT_SERIF,
            max_width=self.WIDTH - 160,
            max_height=(self.HEIGHT - y_cursor) - 110,
            start_size=28,
            min_size=18
        )

        card_y = y_cursor + 45
        for line in body_wrapped:
            draw.text((80, card_y), line, font=body_font, fill=(68, 64, 60))
            card_y += body_font.size + 12

        # Watermark
        draw.text((80, self.HEIGHT - 75), "DEEPSEEK / GROK INSIGHTS", font=badge_font, fill=(120, 113, 108))
        draw.text((self.WIDTH - 160, self.HEIGHT - 75), "VOL. I NO. V", font=badge_font, fill=(120, 113, 108))

        return img

    # ─────────────────────────────────────────────────────────────────────────
    # TEMPLATE 4: Corporate Grid (Minimal Tech, Dark Blue & Cyan Badge)
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_corporate_grid(self, trend_title: str, text: str) -> Image.Image:
        # Navy blue gradient background
        color1 = (13, 27, 42)
        color2 = (27, 38, 59)
        img = self._create_gradient(color1, color2, direction="vertical")
        draw = ImageDraw.Draw(img)

        # Draw a tech-style horizontal rules and dots in corners
        draw.line([(60, 60), (self.WIDTH - 60, 60)], fill=(65, 90, 119), width=1)
        draw.line([(60, self.HEIGHT - 60), (self.WIDTH - 60, self.HEIGHT - 60)], fill=(65, 90, 119), width=1)

        # Fonts
        badge_font = ImageFont.truetype(self.FONT_SANS, 18, index=10) # Medium
        title_font = ImageFont.truetype(self.FONT_SANS, 48, index=1)  # Bold

        # Cyan badge box
        badge_text = "STRATEGIC ANALYSIS"
        badge_w = draw.textbbox((0, 0), badge_text, font=badge_font)[2] - draw.textbbox((0, 0), badge_text, font=badge_font)[0]
        draw.rectangle([(80, 85), (80 + badge_w + 24, 120)], fill=(224, 225, 221), outline=None)
        draw.text((92, 93), badge_text, font=badge_font, fill=(13, 27, 42))

        # Trend Title
        title_wrapped = self._wrap_text(trend_title, title_font, self.WIDTH - 160, draw)
        y_cursor = 145
        for line in title_wrapped[:2]:
            draw.text((80, y_cursor), line, font=title_font, fill=(255, 255, 255))
            y_cursor += 58

        # Body text (draw in white on dark background)
        body_font, body_wrapped, _ = self._get_best_font_size(
            draw=draw,
            text=text,
            font_path=self.FONT_SANS,
            max_width=self.WIDTH - 160,
            max_height=(self.HEIGHT - y_cursor) - 100,
            start_size=30,
            min_size=18,
            index=0 # Regular
        )

        card_y = y_cursor + 35
        for line in body_wrapped:
            draw.text((80, card_y), line, font=body_font, fill=(224, 225, 221))
            card_y += body_font.size + 10

        # Corner decoration dots
        dot_color = (224, 225, 221)
        draw.rectangle([(58, 58), (62, 62)], fill=dot_color)
        draw.rectangle([(self.WIDTH - 62, 58), (self.WIDTH - 58, 62)], fill=dot_color)
        draw.rectangle([(58, self.HEIGHT - 62), (62, self.HEIGHT - 58)], fill=dot_color)
        draw.rectangle([(self.WIDTH - 62, self.HEIGHT - 62), (self.WIDTH - 58, self.HEIGHT - 58)], fill=dot_color)

        return img

    def generate_ai_image(self, prompt: str, output_path: Path) -> bool:
        """
        xAI's grok-imagine-image-quality modelini çağıraraq şəkli çəkir və yükləyir.
        """
        try:
            client = OpenAI(
                api_key=settings.GROK_API_KEY,
                base_url=settings.GROK_BASE_URL,
            )
            response = client.images.generate(
                model="grok-imagine-image-quality",
                prompt=prompt,
            )
            image_url = response.data[0].url
            if not image_url:
                logger.error("❌ Xəta: xAI API heç bir şəkil URL-i qaytarmadı.")
                return False

            # Şəkli yüklə
            res = requests.get(image_url, timeout=30)
            if res.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(res.content)
                logger.info(f"✅ AI şəkli uğurla yükləndi və yadda saxlanıldı: {output_path.name}")
                return True
            else:
                logger.error(f"❌ Şəkil endirmə xətası (status={res.status_code})")
                return False
        except Exception as e:
            logger.error(f"❌ AI şəkil yaradılarkən xəta baş verdi: {e}", exc_info=True)
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Main Generator Endpoint
    # ─────────────────────────────────────────────────────────────────────────
    def generate(self, trend_title: str, body_text: str, output_path: Path, template_index: Optional[int] = None, image_prompt: Optional[str] = None) -> Path:
        """
        Generates a post image card or AI-generated image, saves it to output_path, and returns the path.
        
        Args:
            trend_title: The name of the chosen trend
            body_text: Highlights/body text of the card
            output_path: Target save path
            template_index: Option to lock in template style [0, 1, 2, 3]
            image_prompt: AI generation prompt (if provided, generates image using xAI)
        """
        if image_prompt:
            logger.info(f"🎨 AI ilə mövzuya uyğun şəkil yaradılır: '{image_prompt[:60]}...'")
            if self.generate_ai_image(image_prompt, output_path):
                return output_path
            logger.warning("⚠️  AI ilə şəkil yaradılması alınmadı, Pillow şablonuna keçilir...")
        # Clean text
        body_text = self._clean_text(body_text)
        
        # Choose template
        if template_index is None or not (0 <= template_index <= 3):
            # Select random template
            template_index = random.choice([0, 1, 2, 3])

        # Generate image using selected template
        if self.use_fallback:
            # Fallback basic image if system fonts are missing
            img = Image.new("RGB", (self.WIDTH, self.HEIGHT), (20, 20, 20))
            draw = ImageDraw.Draw(img)
            draw.text((50, 50), f"TREND: {trend_title}", fill=(255, 255, 255))
            draw.text((50, 150), body_text, fill=(200, 200, 200))
        else:
            try:
                if template_index == 0:
                    img = self._draw_neon_cyberpunk(trend_title, body_text)
                elif template_index == 1:
                    img = self._draw_sunset_glow(trend_title, body_text)
                elif template_index == 2:
                    img = self._draw_editorial_light(trend_title, body_text)
                else:
                    img = self._draw_corporate_grid(trend_title, body_text)
            except Exception as e:
                # Basic backup drawing in case of font error
                img = Image.new("RGB", (self.WIDTH, self.HEIGHT), (15, 23, 42))
                draw = ImageDraw.Draw(img)
                draw.text((50, 50), f"TREND: {trend_title}\n\n{body_text}", fill=(255, 255, 255))

        # Save image
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "PNG")
        return output_path

    def _clean_text(self, text: str) -> str:
        """Removes links, trailing dots, hashtags, and formatting characters."""
        # Remove markdown bold/italics
        text = text.replace("**", "").replace("*", "")
        # Remove hashtags
        text = re.sub(r'#\w+', '', text)
        # Remove X reply signs or indicators
        text = re.sub(r'^\d+/\d+\s*', '', text)
        text = text.replace("👇", "").replace("👉", "")
        # Remove excess white space
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
