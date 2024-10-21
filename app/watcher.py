from __future__ import annotations

import asyncio
from logging import getLogger
import time
from typing import TYPE_CHECKING, Literal

from app.models import NetworkUser
from app.tracker import Tracker
from app.utils import compute_logout_timedelta

if TYPE_CHECKING:
    import asqlite

_log = getLogger(__name__)


class Watcher:
    """
    Manages user sessions and database interactions.

    Handles user logins, logouts, maintains in-memory user states, and
    periodically logs out inactive users.
    """

    def __init__(self, *, pool: asqlite.Pool) -> None:
        """
        Initializes the Watcher with a database connection pool.

        Args:
            pool (asqlite.Pool): Database connection pool.
        """
        self.pool: asqlite.Pool = pool
        self.tracker = Tracker(watcher=self)
        self._users: dict[str, NetworkUser] = {}

    async def setup(self) -> Watcher:
        """
        Sets up the database and starts necessary tasks.

        Returns:
            Watcher: The current instance of Watcher.
        """
        async with self.pool.acquire() as connection:
            _log.debug("Executing SQL setup script.")
            with open("app/db/setup.sql") as fp:
                await connection.executescript(fp.read())

        await self._populate_users()

        _log.debug("Starting force logout task.")
        self.logout_task = asyncio.create_task(
            self._logout_task(), name="Watcher force-logout task"
        )

        _log.debug("Starting tracker task.")
        self.tracker_task = asyncio.create_task(
            self.tracker.run(), name="Tracker running task"
        )

        _log.info("Watcher setup completed successfully.")

    async def _populate_users(self) -> dict[str, NetworkUser]:
        """
        Populates the in-memory user dictionary from the database.

        Returns:
            dict[str, NetworkUser]: Mapping of MAC addresses to NetworkUser objects.
        """
        async with self.pool.acquire() as connection:
            query = """
                WITH latest_logins AS (
                    SELECT logins.user_id, 
                        MAX(logins.login_time) AS last_seen 
                    FROM logins 
                    WHERE logins.logout_time IS NULL 
                    GROUP BY logins.user_id
                )
                SELECT users.*, 
                    (ll.user_id IS NOT NULL) AS is_logged_in,
                    ll.last_seen
                FROM users
                LEFT JOIN latest_logins ll ON users.id = ll.user_id;
            """

            rows = await connection.fetchall(query)

        for row in rows:
            user = NetworkUser.from_row(row)
            _log.debug("Adding known user %s.", user)
            self._users[user.mac] = user

        _log.info(
            "Found %d known users: %s.",
            len(self._users),
            ", ".join((user.name for user in self._users.values())),
        )

    async def cleanup(self) -> None:
        """Cancels ongoing tasks and performs cleanup."""
        tasks = [self.logout_task, self.tracker_task]

        for task in tasks:
            if task and not task.done():
                _log.debug("Cancelling task: %s.", task.get_name())
                task.cancel()

        _log.info("Attempting to cancel %d tasks.", len(tasks))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for task, result in zip(tasks, results):
            if isinstance(result, asyncio.CancelledError):
                _log.info("Task %s was successfully cancelled.", task.get_name())
            elif isinstance(result, Exception):
                _log.error("Task %s encountered an error: %s", task.get_name(), result)
            else:
                _log.debug("Task %s completed successfully.", task.get_name())

    async def purge_inactive_users(self) -> None:
        """Logs out users whose sessions have expired."""
        inactive_users = [user for user in self._users.values() if user.is_inactive()]

        for user in inactive_users:
            await self.logout_user(user=user)

        if inactive_users:
            _log.info("Purged %d inactive users.", len(inactive_users))

    async def _logout_task(self) -> None:
        """
        Periodically logs out users at FORCE_LOGOUT_HOUR.

        This runs in an infinite loop, sleeping for a specified duration before
        attempting to log out users still logged in.
        """
        while True:
            sleep_seconds = compute_logout_timedelta()
            _log.debug("Sleeping for %ds.", sleep_seconds)

            await asyncio.sleep(sleep_seconds)
            await self.logout("*")

    def get_user(self, mac: str | Literal["*"]) -> NetworkUser | None:
        """
        Retrieves a user by their MAC address.

        Args:
            mac (str): The MAC address of the user.

        Returns:
            NetworkUser | None: The user object if found, otherwise None.
        """
        return self._users if mac == "*" else self._users.get(mac)

    async def get_total_hours(self) -> list[list[str | float]]:
        """
        Retrieve total hours logged by each user.

        Returns:
            list[list[Union[str, float]]]: A list of users with their logged name, role,
            and total hours.
        """

        query = """SELECT 
                    u.name,
                    u.role,
                    IFNULL(ROUND(SUM(CASE 
                                        WHEN l.logout_time IS NOT NULL 
                                        THEN (l.logout_time - l.login_time) / 3600 
                                        ELSE 0 
                                    END), 3), 0) AS total_hours
                FROM 
                    users u
                LEFT JOIN 
                    logins l ON u.id = l.user_id
                GROUP BY 
                    u.name, u.role;
                """

        async with self.pool.acquire() as connection:
            rows = await connection.fetchall(query)

        return [[row["name"], row["role"], row["total_hours"]] for row in rows]

    async def create_user(self, *, user: NetworkUser) -> None:
        """
        Creates a new user in the database and updates the local user dictionary.

        Args:
            user (NetworkUser): The user object to be created.
        """
        statement = "INSERT INTO users VALUES(:id, :name, :role, :mac);"
        parameters = dict(
            id=user.id,
            name=user.name,
            role=user.role.capitalize(),
            mac=user.mac,
        )

        _log.debug("Creating user %s (%s).", user.name, user.mac)
        self._users[user.mac] = user

        async with self.pool.acquire() as connection:
            await connection.execute(statement, parameters)

        _log.info("Created user: %s.", user.name)

    async def logout_user(self, *, user: NetworkUser | Literal["*"]) -> None:
        """
        Logs out a user by updating their logout time in the database.

        Args:
            user (NetworkUser | Literal["*"]): The user to log out or "*" to log out all users.
        """
        if user.id == "*":
            statement = "UPDATE logins SET logout_time = :logout_time WHERE logout_time IS NULL;"
            parameters = dict(logout_time=time.time())

        else:
            statement = """UPDATE logins SET logout_time = :logout_time
                            WHERE login_id = (
                                SELECT MAX(login_id)
                                FROM logins
                                WHERE user_id = :user_id AND logout_time IS NULL
                            );"""
            parameters = dict(logout_time=time.time(), user_id=user.id)

        users = self._users.values() if user == "*" else [user]

        for user in users:
            _log.debug("Logging out %s (%s).", user.name, user.mac)
            self._users[user.mac].set_logged_in(False)

        async with self.pool.acquire() as connection:
            await connection.execute(statement, parameters)

        name = user if user == "*" else user.name
        _log.info("Logged out %s.", name)

    async def login_user(self, user: NetworkUser) -> None:
        """
        Logs in a user by inserting a new login record in the database.

        Args:
            user (NetworkUser): The user object to log in.
        """
        _log.debug("Logging in %s (%s).", user.name, user.mac)

        self._users[user.mac].set_logged_in(True)

        statement = (
            "INSERT INTO logins (user_id, login_time) VALUES (:user_id, :login_time);"
        )
        parameters = dict(user_id=user.id, login_time=time.time())

        async with self.pool.acquire() as connection:
            await connection.execute(statement, parameters)

        _log.info("Logged in %s.", user.name)
