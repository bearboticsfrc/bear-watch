from __future__ import annotations

import asyncio
import dataclasses
import logging
import re
import time
from typing import TYPE_CHECKING

from app.utils import LoggedInUser, NetworkUser, NmapScanError
from config import *

if TYPE_CHECKING:
    from aiohttp import web

class BearTracker:
    _MAC_REGEX = re.compile(r"(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})")

    def __init__(self, app: web.Application) -> None:
        self.app = app

        self._all_users: dict[str, NetworkUser] = {}
        self._logged_in_users: dict[str, NetworkUser] = {}

        self.setup_logging()

    @property
    def all_users(self) -> dict[str, dict]:
        return {mac: dataclasses.asdict(user) 
                for mac, user 
                in self._all_users.items()}

    @property
    def logged_in_users(self) -> dict[str, dict]:
        return {mac: dataclasses.asdict(user) 
                for mac, user 
                in self._logged_in_users.items()}

    def setup_logging(self) -> None:
        level = getattr(logging, LOGGING_LEVEL.upper())

        handler = logging.FileHandler("logs/tracker.log")
        handler.setLevel(level)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        self.logger = logging.getLogger("bearwatch.tracker")
        self.logger.addHandler(handler)
    
    async def __aenter__(self) -> BearTracker:
        await self._populate_all_users()
        await self._populate_logged_in_users()

        return self

    async def __aexit__(self, *_) -> None:
        pass

    async def _populate_all_users(self) -> None:
        async with self.app["connection"].acquire() as connection:
            rows = await connection.fetchall("SELECT * FROM users;")
            
            for row in rows:
                user = NetworkUser.from_row(row)
                self._all_users[user.mac] = user

    async def _populate_logged_in_users(self) -> None:
        async with self.app["connection"].acquire() as connection:
            rows = await connection.fetchall("SELECT * FROM logins, users WHERE logins.user_id = users.user_id AND logins.logout_time IS NULL;")
            
            for row in rows:
                user = NetworkUser.from_row(row)
                self._logged_in_users[user.mac] = user


    def add_user(self, user: NetworkUser) -> None:
        """Add a user's mac address to the registry"""
        self.logger.debug("Adding user to cache: %s", user)
        
        self._all_users[user.mac] = user

    async def _scan_subnets(self, subnets: list[str]) -> list[str]:
        """Scans provided subnets and returns the MAC addresses of all active devices. 
           
           Arguments:
           subnets -- A list of subnets to scan. Should be in a notation recognized by Nmap.
        """
        self.logger.debug("Scanning subnets: %s", ", ".join(subnets))

        process = await asyncio.create_subprocess_exec(
            "nmap", "-sn", "-n", *subnets, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=120)
        except TimeoutError:
            self.logger.error("Nmap scan timed out. Terminating.")
            process.terminate()

            raise

        if process.returncode != 0:
            self.logger.error("Nmap scan failed with return code: %d", process.returncode)
           
            raise NmapScanError("Nmap scan failed", process.returncode)
        else:
            stdout = stdout.decode()

        return self._MAC_REGEX.findall(stdout)


    async def _logout(self, user: NetworkUser) -> None:
        """Helper method to logout a user
        
        Arguments:
        user -- The user to logout
        """
        self.logger.debug("Logging out user %s (%s) - %s", user.name, user.user_id, user.mac)

        self._logged_in_users.pop(user.mac, None)
        await self.app["watcher"].logout(user)

    async def _login(self, user: NetworkUser) -> None:
        """Helper method to login a user
        
        Arguments:
        user -- The user to login
        """
        self.logger.debug("Logging in user: %s (%s) - %s", user.name, user.user_id, user.mac)

        user.set_last_seen(time.time())
        self._logged_in_users[user.mac] = user

        try:
            await self.app["watcher"].login(user)
        except LoggedInUser:
            self.logger.warning(
                    "Tried to login already logged in user: %s (%s) - %s. Cache may be stale", 
                    user.name, user.user_id, user.mac)
        
    async def run(self) -> None:
        """Run the network scanner for automatic logging in."""

        while True:
            await asyncio.sleep(SCAN_INTERVAL)

            try:
                devices = await self._scan_subnets(SUBNETS)
            except TimeoutError:
                continue
            except Exception as exc:
                self.logger.exception("Nmap scan raised exception")

            if not devices:
                self.logger.debug("Found no devices on subnets: %s", ", ".join(SUBNETS))
                continue

            for mac in devices:
                user = self._all_users.get(mac)

                if not user:
                    continue
                
                if user.mac not in self._logged_in_users:
                    await self._login(user)
                    continue
                
                if (time.time() - user.last_seen) > DEBOUNCE_SECONDS:
                    await self._logout(user)
                else:
                    await self._logged_in_users[user.mac].set_last_seen(time.time())