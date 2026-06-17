"""
X Automation — Əsas Giriş Nöqtəsi

İstifadə:
  python main.py            # Scheduler işə sal (gündə 1 dəfə)
  python main.py --run      # İndi dərhal bir dəfə işlət
  python main.py --test     # Test rejimində işlət (real post göndərilmir)
  python main.py --check    # Yalnız API bağlantılarını yoxla
"""

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from config.settings import settings
from src.logger import setup_logger

console = Console()


def print_banner():
    """Başlanğıc banneri göstərir."""
    banner = Text()
    banner.append("🐦 X Automation", style="bold cyan")
    banner.append(" | ", style="dim")
    banner.append("Grok (xAI)", style="bold yellow")
    banner.append(" → ", style="dim")
    banner.append("DeepSeek", style="bold blue")
    banner.append(" → ", style="dim")
    banner.append("X (Twitter)", style="bold white")

    meta = (
        f"[dim]Saha:[/dim] [green]{settings.BUSINESS_NICHE}[/green]  "
        f"[dim]Vaxt:[/dim] [cyan]{settings.POST_TIME}[/cyan]  "
        f"[dim]Zona:[/dim] [cyan]{settings.TIMEZONE}[/cyan]"
    )
    if settings.DRY_RUN:
        meta += "  [bold red]⚠ TEST REJİMİ[/bold red]"

    console.print(Panel(banner, subtitle=meta, border_style="cyan"))


def cmd_run(dry_run_override: bool = False):
    """Dərhal bir dəfə tam axarı işə salır."""
    if dry_run_override:
        import os
        os.environ["DRY_RUN"] = "true"
        # settings-i yenilə
        settings.DRY_RUN = True

    from src.post_manager import PostManager
    manager = PostManager()
    result = manager.run()

    if result["success"]:
        console.print("\n[bold green]✅ Uğurla tamamlandı![/bold green]")
    else:
        console.print(f"\n[bold red]❌ Xəta: {result['error']}[/bold red]")
        sys.exit(1)


def cmd_video_repost(dry_run_override: bool = False):
    """Dərhal bir dəfə video repost axarını işə salır."""
    if dry_run_override:
        import os
        os.environ["DRY_RUN"] = "true"
        # settings-i yenilə
        settings.DRY_RUN = True

    from src.post_manager import PostManager
    manager = PostManager()
    result = manager.run_video_repost()

    if result["success"]:
        console.print("\n[bold green]✅ Video repost uğurla tamamlandı![/bold green]")
    else:
        console.print(f"\n[bold red]❌ Xəta (Video Repost): {result['error']}[/bold red]")
        sys.exit(1)


def cmd_check():
    """API bağlantılarını yoxlayır."""
    console.print("\n[bold]🔍 API yoxlanışı başlayır...[/bold]\n")

    results = {}

    # X API yoxla
    try:
        from src.twitter_client import TwitterClient
        client = TwitterClient()
        ok = client.verify_credentials()
        results["X (Twitter) API"] = ("✅ Qoşuldu", "green") if ok else ("❌ Xəta", "red")
    except Exception as e:
        results["X (Twitter) API"] = (f"❌ {e}", "red")

    # Grok (xAI) API check
    try:
        from openai import OpenAI
        grok = OpenAI(api_key=settings.GROK_API_KEY, base_url=settings.GROK_BASE_URL)
        grok.chat.completions.create(
            model="grok-3-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5,
        )
        results["Grok API (xAI)"] = ("✅ Connected", "green")
    except Exception as e:
        results["Grok API (xAI)"] = (f"❌ {e}", "red")

    # DeepSeek API yoxla
    try:
        from openai import OpenAI
        ds = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)
        ds.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5,
        )
        results["DeepSeek API"] = ("✅ Qoşuldu", "green")
    except Exception as e:
        results["DeepSeek API"] = (f"❌ {e}", "red")

    for name, (status, color) in results.items():
        console.print(f"  {name:<25} [{color}]{status}[/{color}]")

    all_ok = all(c == "green" for _, (_, c) in results.items())
    if all_ok:
        console.print("\n[bold green]Bütün API-lər işlək vəziyyətdədir! ✅[/bold green]")
    else:
        console.print("\n[bold red]Bəzi API-lərdə problem var. .env faylını yoxlayın.[/bold red]")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="X (Twitter) Avtomatlaşdırma — Groq + DeepSeek",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--run", action="store_true", help="Dərhal bir dəfə işlət")
    parser.add_argument("--test", action="store_true", help="Test rejimində işlət (real post yox)")
    parser.add_argument("--check", action="store_true", help="API bağlantılarını yoxla")
    parser.add_argument("--video-repost", action="store_true", help="Dərhal bir dəfə video repost işlət (real paylaşımla)")
    parser.add_argument("--test-video-repost", action="store_true", help="Test rejimində dərhal video repost işlət (real paylaşım yoxdur)")
    args = parser.parse_args()

    print_banner()

    try:
        settings.validate()
        settings.ensure_dirs()
    except ValueError as e:
        console.print(f"\n[bold red]{e}[/bold red]")
        sys.exit(1)

    if args.check:
        cmd_check()
    elif args.run:
        cmd_run()
    elif args.test:
        cmd_run(dry_run_override=True)
    elif args.video_repost:
        cmd_video_repost()
    elif args.test_video_repost:
        cmd_video_repost(dry_run_override=True)
    else:
        # Standart rejim: scheduler işə sal
        from src.scheduler import start_scheduler
        start_scheduler()


if __name__ == "__main__":
    main()
