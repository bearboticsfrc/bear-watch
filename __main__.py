from __future__ import annotations

import logging
import sys
from pathlib import Path

import asqlite
from aiohttp import web

from app.watcher import Watcher
from app.web import Web
from config import DATABASE, LOGGING_FORMATTER, LOGGING_LEVEL


def setup_logging() -> None:
    """
    Configures the logging settings for the application.
    """
    logging.basicConfig(level=LOGGING_LEVEL)

    # Create file handlers for specific loggers
    for logger in ("main", "app.tracker", "app.watcher"):
        handler = logging.FileHandler(f"logs/{logger}.log")
        handler.setLevel(LOGGING_LEVEL)
        handler.setFormatter(LOGGING_FORMATTER)
        logging.getLogger(logger).addHandler(handler)


async def startup_hook(app: web.Application) -> None:
    """
    Initializes the application on startup.

    Connects to the database and sets up the Watcher.

    Args:
        app (web.Application): The web application instance.
    """
    logger = logging.getLogger("main")
    path = Path(DATABASE).resolve()
    logger.debug("Connecting to database: %s", path)

    pool = await asqlite.create_pool(path, size=5)
    app["watcher"] = watcher = Watcher(pool=pool)

    await watcher.setup()


async def cleanup_hook(app: web.Application) -> None:
    """
    Cleans up resources on application shutdown.

    Args:
        app (web.Application): The web application instance being shut down.
    """
    watcher: Watcher = app["watcher"]
    await watcher.cleanup()


def main() -> None:
    """
    Main function to start the application.

    Sets up logging and starts the web application with lifecycle hooks.
    """
    setup_logging()
    Web().start(startup_hook=startup_hook, cleanup_hook=cleanup_hook)


if __name__ == "__main__":
    main()
