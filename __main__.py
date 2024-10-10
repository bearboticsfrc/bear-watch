from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import asqlite
from aiohttp import web

from app.tracker import BearTracker
from app.watcher import BearWatch
from app.web import BearWeb
from config import DATABASE, LOGGING_LEVEL

LOGGER = logging.getLogger("bearwatch.main")

def setup_logging() -> None:
        level = getattr(logging, LOGGING_LEVEL.upper())

        handler = logging.FileHandler("logs/main.log")
        handler.setLevel(level)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        LOGGER.addHandler(handler)
        logging.basicConfig(level=level, handlers=[])

async def startup_hook(app: web.Application) -> None:
    LOGGER.debug("Connecting to database: %s", DATABASE)
    app["connection"] = c = await asqlite.create_pool(Path(DATABASE).resolve())
    (await c.acquire()).fetchall
    LOGGER.info("Initalizing BearWatch")
    async with BearWatch(app=app) as watcher:
        app["watcher"] = watcher

    LOGGER.info("Initalizing BearTracker")
    async with BearTracker(app=app) as tracker:        
        app["tracker"] = tracker

    LOGGER.info("Starting BearTracker task")
    asyncio.create_task(tracker.run(), name="BearTracker")

async def cleanup_hook(app: web.Application) -> None:
    LOGGER.debug("Closing connection to database")

    await app["connection"].close()

def main() -> None:
    setup_logging()

    BearWeb().start(startup_hook=startup_hook, cleanup_hook=cleanup_hook)

if __name__ == "__main__":
    main()