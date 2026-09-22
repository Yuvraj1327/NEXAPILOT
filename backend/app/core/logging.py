"""Centralized logging configuration.

Kept deliberately simple (stdlib logging, no external log aggregation
dependency) — a hackathon backend doesn't need more than "structured,
leveled, readable" console output. Swap the handler for a JSON formatter
or shipper later without touching call sites, since every module logs via
`logging.getLogger("nexapilot.<area>")`.
"""

import logging

from app.core.config import settings


def configure_logging() -> None:
    level = logging.DEBUG if settings.debug else logging.INFO

    root_logger = logging.getLogger("nexapilot")
    if root_logger.handlers:
        return  # already configured (e.g. re-imported in tests)

    root_logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    root_logger.addHandler(handler)
    root_logger.propagate = False
