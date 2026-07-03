"""Centralized logging configuration for the whole application."""

import logging
import sys
from pathlib import Path


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root logging handlers (console + rotating file).

    Args:
        log_level: Minimum log level name, e.g. "INFO", "DEBUG".
    """
    Path("logs").mkdir(exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    try:
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            "logs/app.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except OSError:
        # Filesystem may be read-only in some deployment targets; console
        # logging alone is still functional.
        root_logger.warning("File logging unavailable; continuing with console logging only.")

    # Quiet down noisy third-party loggers.
    for noisy in ("httpx", "httpcore", "sentence_transformers", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
