"""
X Automation — Log Sistemi
Həm konsola (rəngli), həm də fayla yazır.
"""

import logging
import sys
from pathlib import Path
from rich.logging import RichHandler
from rich.console import Console

console = Console()


def setup_logger(name: str, log_file: Path, level: str = "INFO") -> logging.Logger:
    """
    Uyğun formatda logger qurur.

    Args:
        name:     Logger adı (adətən modul adı)
        log_file: Log faylının yolu
        level:    Log səviyyəsi (DEBUG, INFO, WARNING, ERROR)
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger  # Artıq qurulub

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Konsol handler (Rich ilə rəngli çıxış) ───────────────────────────────
    rich_handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(rich_handler)

    # ── Fayl handler ─────────────────────────────────────────────────────────
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
