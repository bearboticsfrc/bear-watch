from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING

from app.utils import *
from config import *

if TYPE_CHECKING:
    from asyncio import Task

    from aiohttp import web

class BearWatch:
    def __init__(self, app: web.Application) -> None:
        self.app = app
        self.task: Task

        self.setup_logging()
        
    def setup_logging(self) -> None:
        handler = logging.FileHandler("logs/watcher.log")
        handler.setLevel(LOGGING_LEVEL)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        self.logger = logging.getLogger("bearwatch.watcher")
        self.logger.addHandler(handler)

    async def __aenter__(self) -> BearWatch:
        async with self.app["connection"].cursor() as cursor:
            self.logger.debug("Executing SQL setup script")

            with open("setup.sql") as fp:
                await cursor.executescript(fp.read())

            await self.app["connection"].commit()
            await cursor.execute(
                "SELECT * FROM logins, users WHERE logins.user_id = users.user_id AND logout_time IS NULL;")
            
            current_users = await cursor.fetchall()

        self.current_users = {row["user_id"]: User.from_row(row) for row in current_users}

        self.logger.debug("Starting force logout task")
        self.task = asyncio.create_task(self.logout_task(), name="BearWatch Force Logout")

        return self

    async def __aexit__(self, *_) -> None:
        self.task.cancel()

    def _compute_timedelta(self) -> float:
        dt = datetime.now().replace(hour=FORCE_LOGOUT_HOUR, minute=0, second=0)

        if datetime.now().hour >= FORCE_LOGOUT_HOUR:
            dt += datetime.timedelta(days=1)

        return (dt - datetime.now()).total_seconds()

    async def logout_task(self) -> None:
        while True:
            await asyncio.sleep(self._compute_timedelta())
            await self.logout("*")

    async def create(self, user: NetworkUser) -> None:
        statement = ("INSERT INTO users VALUES(?, ?, ?, ?);", (user.user_id, user.name, user.role, user.mac))

        self.logger.debug("Executing: %s", statement)

        async with self.app["connection"].cursor() as cursor:
            await cursor.execute(*statement)
            await self.app["connection"].commit()

        self.app["tracker"].add_user(user)

    async def logout(self, user: NetworkUser) -> None:
        if user.user_id == "*":
            statement = ("UPDATE logins SET logout_time = ? WHERE logout_time IS NULL;", time.time())
        else:
            statement = ("""UPDATE logins
                            SET logout_time = ?
                            WHERE login_id = (
                                SELECT MAX(login_id)
                                FROM logins
                                WHERE user_id = ? AND logout_time IS NULL
                            );""", (user.last_seen, user.user_id))

        self.logger.debug("Executing: %s", statement)

        async with self.app["connection"].cursor() as cursor:
            await cursor.execute(*statement)
            await self.app["connection"].commit()

    async def login(self, user: User) -> str:
        async with self.app["connection"].cursor() as cursor:
            statement = ("SELECT * FROM logins WHERE user_id = ? AND logout_time IS NULL;", user.user_id)
            self.logger.debug("Executing: %s", statement)

            await cursor.execute(*statement)
            login = await cursor.fetchone()
            
            if login is not None:
                raise LoggedInUser
 
            statement = ("INSERT INTO logins (user_id, login_time) VALUES(?, ?);", (user.user_id, time.time()))
            self.logger.debug("Executing: %s", statement)

            await cursor.execute(*statement)
            await self.app["connection"].commit()